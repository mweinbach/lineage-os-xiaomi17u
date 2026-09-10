// SPDX-License-Identifier: Apache-2.0
package com.android.server.cameraopt;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.PackageManagerInternal;
import android.os.Binder;
import android.os.Handler;
import android.os.Process;
import android.os.SystemClock;
import android.os.SystemProperties;
import android.os.UserHandle;
import android.util.Slog;

import com.android.internal.util.DumpUtils;
import com.android.server.LocalServices;
import com.android.server.ServiceThread;
import com.android.server.SystemService;
import com.android.server.am.NezhaCameraProcessPolicy;
import com.android.server.am.NezhaCameraReclaimPolicy;
import com.miui.cameraopt.ICameraOptManager;
import com.miui.cameraopt.configs.JsonDisptcher;
import com.miui.cameraopt.verify.Verifier;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.FileDescriptor;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayDeque;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Explicit Nezha CameraOpt integration candidate.
 *
 * The runtime factory JAR owns the IPC Stub, the complete Verifier and the
 * configuration loader that decodes the encrypted CameraOpt tables. This
 * service preserves its verification decisions and boot hook, feeds the
 * decoded reclaim table to an authored policy in services.jar, and implements
 * the four app-reachable methods on that policy. Unported API operations
 * throw and remain visible in dumps; they never return a fabricated result or
 * count as implemented performance behavior.
 */
public final class NezhaCameraOptService extends SystemService {
    private static final String TAG = "NezhaCameraOpt";
    private static final String CAMERA_PACKAGE = "com.android.camera";
    private static final String ENABLE_PROPERTY = "ro.nezha.cameraopt.service";
    /** Factory CameraPerfWatcher gate; the watcher itself is not ported. */
    private static final String PERF_WATCHER_PROPERTY = "persist.miui.camera.perfwatcher.enable";
    /** Factory JsonDisptcher section consumed by the reclaim policy. */
    private static final String RECLAIM_SECTION = "CameraReclaim";
    /** Factory CameraCloundSync property prefix. */
    private static final String CLOUD_PROPERTY_PREFIX = "persist.vendor.camera.cloud";
    private static final int MAX_EVENT_CHARS = 16 * 1024;
    private static final int MAX_CLOUD_CHARS = 256 * 1024;
    private static final int MAX_NAME_CHARS = 256;
    private static final int MAX_PROPERTY_VALUE_CHARS = 91;
    private static final int MAX_CLOUD_PROPERTIES = 64;
    private static final int MAX_PERFORMANCE_HISTORY = 32;
    private static final int MAX_CLOUD_HISTORY = 8;
    private static final int EVENT_CAMERA_OPEN = 3;
    private static final int EVENT_CAMERA_CLOSE = 4;

    private final Object mStatsLock = new Object();
    private final Map<String, Long> mCalls = new LinkedHashMap<>();
    private final Map<String, Long> mUnsupported = new LinkedHashMap<>();
    private final Map<String, Long> mEventCounts = new LinkedHashMap<>();
    private final Map<String, Long> mModeLevels = new LinkedHashMap<>();
    private final ArrayDeque<String> mPerformanceTimes = new ArrayDeque<>();
    private final ArrayDeque<String> mCloudHistory = new ArrayDeque<>();
    private final Map<String, Long> mCloudProperties = new LinkedHashMap<>();
    private long mPerformanceTimesDropped;
    private long mCloudAccepted;
    private long mCloudRejected;
    private long mCloudPropertiesSet;
    private long mCloudPropertiesFailed;
    private long mCloudMemReserveIgnored;
    private long mLastCaptureReclaimRequestUptime;
    private ServiceThread mThread;
    private Handler mHandler;
    private PackageManagerInternal mPackageManagerInternal;
    private CameraStatusSampler mStatus;
    private NezhaCameraProcessPolicy mProcessPolicy;
    private NezhaCameraReclaimPolicy mReclaimPolicy;
    private Verifier mVerifier;
    private volatile boolean mBootCallbackCompleted;
    private volatile Boolean mLastVerificationResult;
    private volatile Throwable mNativeInitializationFailure;
    private volatile String mConfigurationState = "not loaded";
    private volatile Throwable mConfigurationFailure;
    private volatile long mConfigurationDeliveries;

    public NezhaCameraOptService(Context context) {
        super(context);
        if (!SystemProperties.getBoolean(ENABLE_PROPERTY, false)) {
            throw new IllegalStateException("CameraOpt service was not selected by this product");
        }
    }

    @Override
    public void onStart() {
        mPackageManagerInternal = LocalServices.getService(PackageManagerInternal.class);
        if (mPackageManagerInternal == null) {
            throw new IllegalStateException("PackageManagerInternal must precede CameraOpt");
        }
        // Preserve the original singleton and its real captured PackageManagerInternal.
        // Resolve it before allocating a worker or registering process observers.
        mVerifier = Verifier.getInstance();
        mThread = new ServiceThread(TAG, Process.THREAD_PRIORITY_BACKGROUND, true);
        mThread.start();
        try {
            mHandler = new Handler(mThread.getLooper());
            mStatus = new CameraStatusSampler(getContext(), mHandler);
            mProcessPolicy = new NezhaCameraProcessPolicy(getContext(), mHandler);
            mReclaimPolicy = new NezhaCameraReclaimPolicy(getContext(), mHandler);
            publishBinderService("cameraopt", new CameraOptBinder());
        } catch (RuntimeException | LinkageError error) {
            if (mReclaimPolicy != null) {
                try {
                    mReclaimPolicy.close();
                } catch (RuntimeException | LinkageError cleanupError) {
                    error.addSuppressed(cleanupError);
                }
            }
            if (mProcessPolicy != null) {
                try {
                    mProcessPolicy.close();
                } catch (RuntimeException | LinkageError cleanupError) {
                    error.addSuppressed(cleanupError);
                }
            }
            mThread.quitSafely();
            throw error;
        }
        // The factory loader decodes the on-device tables through its JNI. Keep that
        // file work off the boot thread; requests before it completes see no table.
        if (!mHandler.post(this::loadConfiguration)) {
            mConfigurationState = "not scheduled";
        }
        Slog.i(TAG, "Published CameraOpt candidate; unsupported API calls remain errors");
    }

    @Override
    public void onBootPhase(int phase) {
        if (phase == PHASE_BOOT_COMPLETED) {
            // The original method invokes initPropCache and discards its result.
            // A completed callback does not by itself establish a true verifier result.
            try {
                mVerifier.onBootCompleted();
                mBootCallbackCompleted = true;
                Slog.i(TAG, "Original CameraOpt boot-completion callback completed");
            } catch (RuntimeException | LinkageError error) {
                mNativeInitializationFailure = error;
                mLastVerificationResult = null;
                Slog.e(TAG, "Original CameraOpt native initialization is unavailable", error);
            }
        }
    }

    /** Factory CameraOptManagerService startup: JsonDisptcher.loadJson then callbacks. */
    private void loadConfiguration() {
        try {
            JsonDisptcher dispatcher = JsonDisptcher.getInstance();
            dispatcher.loadJson();
            // Registration delivers the section immediately when the merged table has it.
            dispatcher.registerDataCallback(RECLAIM_SECTION, mReclaimConfiguration);
            mConfigurationState = mConfigurationDeliveries > 0 ? "loaded" : "loaded without "
                    + RECLAIM_SECTION;
            Slog.i(TAG, "CameraOpt configuration " + mConfigurationState);
        } catch (RuntimeException | LinkageError error) {
            mConfigurationFailure = error;
            mConfigurationState = "failed";
            Slog.e(TAG, "Original CameraOpt configuration loader failed", error);
        }
    }

    private final JsonDisptcher.DataCallback mReclaimConfiguration =
            new JsonDisptcher.DataCallback() {
                @Override
                public void onDataCallback(JSONObject section) {
                    mConfigurationDeliveries++;
                    mReclaimPolicy.setConfiguration(section);
                }

                @Override
                public void dumpConfigs() {
                    // The factory dumps its parsed table here; the policy dump does that.
                }
            };

    private static final class Caller {
        final int uid;
        final int pid;

        Caller(int uid, int pid) {
            this.uid = uid;
            this.pid = pid;
        }
    }

    private Caller requireCaller() {
        final int uid = Binder.getCallingUid();
        final int pid = Binder.getCallingPid();
        if (uid == Process.SYSTEM_UID || uid == Process.CAMERASERVER_UID) {
            return new Caller(uid, pid);
        }
        final int expectedUid;
        try {
            expectedUid = getContext().getPackageManager().getPackageUidAsUser(
                    CAMERA_PACKAGE, UserHandle.getUserId(uid));
        } catch (PackageManager.NameNotFoundException error) {
            throw new SecurityException("Camera package is unavailable", error);
        }
        if (uid != expectedUid || !mPackageManagerInternal.isPlatformSigned(CAMERA_PACKAGE)) {
            throw new SecurityException("CameraOpt requires the real platform-signed camera caller");
        }
        return new Caller(uid, pid);
    }

    private void count(Map<String, Long> counters, String name) {
        synchronized (mStatsLock) {
            counters.put(name, counters.getOrDefault(name, 0L) + 1L);
        }
    }

    private UnsupportedOperationException unsupported(String method) {
        requireCaller();
        final long count;
        synchronized (mStatsLock) {
            count = mUnsupported.getOrDefault(method, 0L) + 1L;
            mUnsupported.put(method, count);
        }
        // Keep every occurrence in the counter while bounding repeated log output.
        if (count <= 3 || (count & (count - 1)) == 0) {
            Slog.w(TAG, "Unsupported CameraOpt API " + method + " (attempt " + count + ")");
        }
        return new UnsupportedOperationException("Unported CameraOpt API: " + method);
    }

    private static String bounded(String value, int limit) {
        if (value == null) {
            return "null";
        }
        return value.length() <= limit ? value : value.substring(0, limit) + "...";
    }

    private static String sha256(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            StringBuilder builder = new StringBuilder();
            for (byte item : digest.digest(text.getBytes(StandardCharsets.UTF_8))) {
                builder.append(String.format("%02x", item));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException error) {
            return "unavailable";
        }
    }

    private static boolean validPropertyToken(String token) {
        if (token == null || token.isEmpty() || token.length() > MAX_NAME_CHARS) {
            return false;
        }
        for (int i = 0; i < token.length(); i++) {
            char c = token.charAt(i);
            boolean ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                    || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.';
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    /**
     * Factory CameraCloundSync.updateCloudData: property module, dispatcher merge,
     * memory-reserve refresh. The last part is not ported; its keys are counted.
     */
    private void applyCloudData(double version, String json, String digest) {
        final JSONObject object;
        try {
            object = new JSONObject(json);
        } catch (JSONException error) {
            synchronized (mStatsLock) {
                mCloudRejected++;
                remember(mCloudHistory, MAX_CLOUD_HISTORY, "version=" + version + " sha256="
                        + digest + " rejected: not a JSON object");
            }
            return;
        }
        int set = 0;
        int failed = 0;
        int seen = 0;
        JSONObject modules = object.optJSONObject("properties");
        if (modules != null) {
            Iterator<String> moduleNames = modules.keys();
            while (moduleNames.hasNext() && seen < MAX_CLOUD_PROPERTIES) {
                String module = moduleNames.next();
                JSONObject values = modules.optJSONObject(module);
                if (values == null || !validPropertyToken(module)) {
                    continue;
                }
                Iterator<String> keys = values.keys();
                while (keys.hasNext() && seen < MAX_CLOUD_PROPERTIES) {
                    String key = keys.next();
                    String value = values.optString(key, null);
                    if (value == null || !validPropertyToken(key)
                            || value.length() > MAX_PROPERTY_VALUE_CHARS) {
                        continue;
                    }
                    seen++;
                    String name = CLOUD_PROPERTY_PREFIX + "." + module + "." + key;
                    boolean ok;
                    try {
                        // Vendor policy owns this property type; a denial is recorded, not hidden.
                        SystemProperties.set(name, value);
                        ok = true;
                    } catch (RuntimeException error) {
                        ok = false;
                    }
                    synchronized (mStatsLock) {
                        mCloudProperties.put(name + (ok ? " set" : " failed"),
                                mCloudProperties.getOrDefault(name + (ok ? " set" : " failed"), 0L)
                                        + 1L);
                    }
                    if (ok) {
                        set++;
                    } else {
                        failed++;
                    }
                }
            }
        }
        boolean accepted;
        String dispatcherState;
        try {
            accepted = JsonDisptcher.getInstance().updateCloudData(version, object);
            dispatcherState = accepted ? "merged" : "not newer";
        } catch (RuntimeException | LinkageError error) {
            accepted = false;
            dispatcherState = "dispatcher error: " + error.getClass().getSimpleName();
        }
        boolean memReserve = object.has("MemReserve_enable") || object.has("MemReserveWatcher");
        synchronized (mStatsLock) {
            mCloudPropertiesSet += set;
            mCloudPropertiesFailed += failed;
            if (accepted) {
                mCloudAccepted++;
            } else {
                mCloudRejected++;
            }
            if (memReserve) {
                mCloudMemReserveIgnored++;
            }
            remember(mCloudHistory, MAX_CLOUD_HISTORY, "version=" + version + " sha256=" + digest
                    + " properties=" + set + "/" + failed + " dispatcher=" + dispatcherState
                    + (memReserve ? " memReserveIgnored" : ""));
        }
    }

    private static void remember(ArrayDeque<String> history, int limit, String line) {
        if (history.size() >= limit) {
            history.removeFirst();
        }
        history.addLast(line);
    }

    private final class CameraOptBinder extends ICameraOptManager.Stub {
        @Override
        public void adjBoost(String packageName, int requestedAdj, long durationMillis, int userId) {
            final Caller caller = requireCaller();
            if (!CAMERA_PACKAGE.equals(packageName) || userId != UserHandle.getUserId(caller.uid)) {
                throw new SecurityException("CameraOpt adjustment must identify the actual caller");
            }
            count(mCalls, "adjBoost");
            mProcessPolicy.adjBoost(caller.uid, caller.pid, packageName,
                    requestedAdj, durationMillis, userId);
        }

        @Override
        public String getSystemStatusJson(int flags) {
            requireCaller();
            count(mCalls, "getSystemStatusJson");
            return mStatus.sample(flags);
        }

        @Override
        public boolean getVerifyResult() {
            requireCaller();
            count(mCalls, "getVerifyResult");
            if (mNativeInitializationFailure != null) {
                throw new IllegalStateException("Original CameraOpt initialization failed",
                        mNativeInitializationFailure);
            }
            try {
                final boolean result = mVerifier.getVerifyResult();
                mLastVerificationResult = result;
                return result;
            } catch (RuntimeException | LinkageError error) {
                mNativeInitializationFailure = error;
                mLastVerificationResult = null;
                Slog.e(TAG, "Original CameraOpt verification is unavailable", error);
                throw new IllegalStateException("Original CameraOpt verification failed", error);
            }
        }

        @Override
        public void notifyCameraPostProcessState() {
            final Caller caller = requireCaller();
            count(mCalls, "notifyCameraPostProcessState");
            mProcessPolicy.onPostProcessComplete(caller.uid, caller.pid);
        }

        @Override
        public void sendCameraEvent(int event, String payload) {
            final Caller caller = requireCaller();
            if (event != 0 && event != 3 && event != 4 && event != 7 && event != 8) {
                throw unsupported("sendCameraEvent:unknownId");
            }
            if (payload == null || payload.length() > MAX_EVENT_CHARS) {
                throw new IllegalArgumentException("Camera event must be a bounded JSON object");
            }
            try {
                new JSONObject(payload);
            } catch (JSONException error) {
                throw new IllegalArgumentException("Camera event payload is not a JSON object", error);
            }
            count(mCalls, "sendCameraEvent");
            count(mEventCounts, Integer.toString(event));
            mProcessPolicy.onCameraEvent(caller.uid, caller.pid, event, payload);
            // The factory reclaim manager keys its kill spacing to camera foreground
            // time and drops its mode level on close; these events are the nearest producers.
            if (event == EVENT_CAMERA_OPEN) {
                mReclaimPolicy.onCameraOpened(caller.uid, caller.pid);
            } else if (event == EVENT_CAMERA_CLOSE) {
                mReclaimPolicy.onCameraClosed(caller.uid, caller.pid);
            }
            // These are camera client events, not the factory's earlier activity-start
            // notification. Do not fabricate before-launch status history from them.
        }

        @Override
        public void reportMemPressure(int pressure) {
            requireCaller();
            count(mCalls, "reportMemPressure");
            // The exact factory implementation returns immediately for this method.
        }

        @Override
        public void boostCameraByThreshold(long threshold) {
            final Caller caller = requireCaller();
            if (threshold == 0) {
                // The factory zero level drives its vendor performance wrapper and a
                // delayed system-server GC; neither is ported and the app never sends it.
                throw unsupported("boostCameraByThreshold:zero");
            }
            count(mCalls, "boostCameraByThreshold");
            count(mModeLevels, "0x" + Long.toHexString(threshold));
            if (!mReclaimPolicy.onModeLevel(caller.uid, caller.pid, threshold)) {
                count(mEventCounts, "modeLevelIgnored");
            }
        }

        @Override
        public void reclaimMemoryForCamera(long modeId, int first, int second) {
            final Caller caller = requireCaller();
            count(mCalls, "reclaimMemoryForCamera");
            synchronized (mStatsLock) {
                mLastCaptureReclaimRequestUptime = SystemClock.uptimeMillis();
            }
            // The factory also opens a short restart-interception window here; its
            // consumer is a MIUI activity-manager hook that this platform does not have.
            mReclaimPolicy.onCaptureReclaim(caller.uid, caller.pid, modeId, first, second);
        }

        @Override
        public void notifyCameraPerformanceTime(String event, String mode, long costMillis) {
            requireCaller();
            if (event == null || event.length() > MAX_NAME_CHARS
                    || (mode != null && mode.length() > MAX_NAME_CHARS)) {
                throw new IllegalArgumentException("Performance event must be bounded text");
            }
            count(mCalls, "notifyCameraPerformanceTime");
            synchronized (mStatsLock) {
                if (mPerformanceTimes.size() >= MAX_PERFORMANCE_HISTORY) {
                    mPerformanceTimes.removeFirst();
                    mPerformanceTimesDropped++;
                }
                mPerformanceTimes.addLast(SystemClock.uptimeMillis() + "ms " + event + " ["
                        + bounded(mode, 64) + "] cost=" + costMillis);
            }
            // With the watcher property off, the factory only logs the event. The
            // enabled watcher (thresholds, trace capture) is not ported.
            if (SystemProperties.getBoolean(PERF_WATCHER_PROPERTY, false)) {
                throw unsupported("notifyCameraPerformanceTime:watcher");
            }
        }

        @Override
        public void updateCloudData(double version, String json) {
            requireCaller();
            if (json == null || json.isEmpty() || json.length() > MAX_CLOUD_CHARS) {
                throw new IllegalArgumentException("Cloud data must be bounded JSON text");
            }
            count(mCalls, "updateCloudData");
            final String digest = sha256(json);
            if (!mHandler.post(() -> applyCloudData(version, json, digest))) {
                synchronized (mStatsLock) {
                    mCloudRejected++;
                }
            }
        }

        @Override
        public String getSecretKey() {
            throw unsupported("getSecretKey");
        }

        @Override
        public boolean interceptAppRestartIfNeeded(String arg0, String arg1, int arg2, int arg3) {
            throw unsupported("interceptAppRestartIfNeeded");
        }

        @Override
        public boolean isCameraInForeground() {
            throw unsupported("isCameraInForeground");
        }

        @Override
        public boolean isCameraScene() {
            throw unsupported("isCameraScene");
        }

        @Override
        public boolean isHasCaptureTask() {
            throw unsupported("isHasCaptureTask");
        }

        @Override
        public void notify3rdAppProviderUsed(String arg0, String arg1) {
            throw unsupported("notify3rdAppProviderUsed");
        }

        @Override
        public void notifyActivityChanged(ComponentName arg0) {
            throw unsupported("notifyActivityChanged");
        }

        @Override
        public void notifyActivityDisplayChange(int arg0, int arg1, String arg2, String arg3, String arg4, int arg5, int arg6, int arg7, int arg8) {
            throw unsupported("notifyActivityDisplayChange");
        }

        @Override
        public void notifyActivityStart(Intent arg0) {
            throw unsupported("notifyActivityStart");
        }

        @Override
        public void notifyActivityStateChange(int arg0, int arg1, String arg2, String arg3, String arg4, int arg5, int arg6, int arg7) {
            throw unsupported("notifyActivityStateChange");
        }

        @Override
        public void notifyCameraStatusChanged(String arg0, String arg1, String arg2, int arg3, int arg4, int arg5) {
            throw unsupported("notifyCameraStatusChanged");
        }

        @Override
        public void notifyFocusWindowChanged(int arg0, int arg1, int arg2, String arg3) {
            throw unsupported("notifyFocusWindowChanged");
        }

        @Override
        public void notifyProcessDied(int arg0, int arg1, String arg2, String arg3) {
            throw unsupported("notifyProcessDied");
        }

        @Override
        public void notifyProcessStarted(int arg0, int arg1, String arg2, String arg3) {
            throw unsupported("notifyProcessStarted");
        }

        @Override
        public void notifyStartActivityFinish(Intent arg0, int arg1, long arg2, long arg3) {
            throw unsupported("notifyStartActivityFinish");
        }

        @Override
        public void onTransitionAnimateStateChanged(boolean arg0, int arg1) {
            throw unsupported("onTransitionAnimateStateChanged");
        }

        @Override
        public void relayoutWindow(int arg0, int arg1, int arg2, String arg3, String arg4, int arg5, int arg6, int arg7, int arg8, int arg9, int arg10) {
            throw unsupported("relayoutWindow");
        }

        @Override
        public void removeWindow(int arg0, int arg1, int arg2, String arg3, String arg4) {
            throw unsupported("removeWindow");
        }

        @Override
        protected void dump(FileDescriptor fd, PrintWriter writer, String[] args) {
            if (!DumpUtils.checkDumpPermission(getContext(), TAG, writer)) {
                return;
            }
            writer.println("CameraOpt source candidate; a present service is not capture acceptance");
            writer.println("boot_callback_completed=" + mBootCallbackCompleted);
            writer.println("native_initialization_failure=" + mNativeInitializationFailure);
            writer.println("last_original_verifier_result=" + mLastVerificationResult);
            writer.println("configuration_state=" + mConfigurationState
                    + " deliveries=" + mConfigurationDeliveries
                    + " failure=" + mConfigurationFailure);
            synchronized (mStatsLock) {
                writer.println("implemented_api_attempts=" + mCalls);
                writer.println("unsupported_api_attempts=" + mUnsupported);
                writer.println("camera_event_attempts=" + mEventCounts);
                writer.println("mode_level_attempts=" + mModeLevels);
                writer.println("last_capture_reclaim_request_uptime_ms="
                        + mLastCaptureReclaimRequestUptime);
                writer.println("cloud_updates: accepted=" + mCloudAccepted + " rejected="
                        + mCloudRejected + " propertiesSet=" + mCloudPropertiesSet
                        + " propertiesFailed=" + mCloudPropertiesFailed
                        + " memReserveIgnored=" + mCloudMemReserveIgnored);
                for (String line : mCloudHistory) {
                    writer.println("  cloud " + line);
                }
                if (!mCloudProperties.isEmpty()) {
                    writer.println("  cloud_properties=" + mCloudProperties);
                }
                writer.println("performance_times: retained=" + mPerformanceTimes.size()
                        + " dropped=" + mPerformanceTimesDropped + " watcherRequested="
                        + SystemProperties.getBoolean(PERF_WATCHER_PROPERTY, false));
                for (String line : mPerformanceTimes) {
                    writer.println("  perf " + line);
                }
            }
            mStatus.dump(writer);
            mProcessPolicy.dump(writer);
            mReclaimPolicy.dump(writer);
        }
    }
}
