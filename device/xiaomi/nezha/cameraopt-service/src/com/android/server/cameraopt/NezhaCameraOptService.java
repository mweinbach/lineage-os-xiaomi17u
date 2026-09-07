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
import android.os.SystemProperties;
import android.os.UserHandle;
import android.util.Slog;

import com.android.internal.util.DumpUtils;
import com.android.server.LocalServices;
import com.android.server.ServiceThread;
import com.android.server.SystemService;
import com.android.server.am.NezhaCameraProcessPolicy;
import com.miui.cameraopt.ICameraOptManager;
import com.miui.cameraopt.verify.Verifier;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.FileDescriptor;
import java.io.PrintWriter;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Explicit Nezha CameraOpt integration candidate.
 *
 * The runtime factory JAR owns the IPC Stub and the complete Verifier. This
 * service preserves its verification decisions and boot hook. Unported API
 * operations throw and remain visible in dumps; they never return a fabricated
 * result or count as implemented performance behavior.
 */
public final class NezhaCameraOptService extends SystemService {
    private static final String TAG = "NezhaCameraOpt";
    private static final String CAMERA_PACKAGE = "com.android.camera";
    private static final String ENABLE_PROPERTY = "ro.nezha.cameraopt.service";
    private static final int MAX_EVENT_CHARS = 16 * 1024;

    private final Object mStatsLock = new Object();
    private final Map<String, Long> mCalls = new LinkedHashMap<>();
    private final Map<String, Long> mUnsupported = new LinkedHashMap<>();
    private final Map<String, Long> mEventCounts = new LinkedHashMap<>();
    private ServiceThread mThread;
    private Handler mHandler;
    private PackageManagerInternal mPackageManagerInternal;
    private CameraStatusSampler mStatus;
    private NezhaCameraProcessPolicy mProcessPolicy;
    private Verifier mVerifier;
    private volatile boolean mBootCallbackCompleted;
    private volatile Boolean mLastVerificationResult;
    private volatile Throwable mNativeInitializationFailure;

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
            publishBinderService("cameraopt", new CameraOptBinder());
        } catch (RuntimeException | LinkageError error) {
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
        public void boostCameraByThreshold(long arg0) {
            throw unsupported("boostCameraByThreshold");
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
        public void notifyCameraPerformanceTime(String arg0, String arg1, long arg2) {
            throw unsupported("notifyCameraPerformanceTime");
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
        public void reclaimMemoryForCamera(long arg0, int arg1, int arg2) {
            throw unsupported("reclaimMemoryForCamera");
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
        public void updateCloudData(double arg0, String arg1) {
            throw unsupported("updateCloudData");
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
            synchronized (mStatsLock) {
                writer.println("implemented_api_attempts=" + mCalls);
                writer.println("unsupported_api_attempts=" + mUnsupported);
                writer.println("camera_event_attempts=" + mEventCounts);
            }
            mStatus.dump(writer);
            mProcessPolicy.dump(writer);
        }
    }
}
