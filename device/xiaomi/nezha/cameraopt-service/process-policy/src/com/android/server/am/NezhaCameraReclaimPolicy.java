/*
 * Copyright (C) 2026 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.server.am;

import android.app.ActivityManager;
import android.app.ActivityTaskManager;
import android.app.ApplicationExitInfo;
import android.content.ComponentName;
import android.content.Context;
import android.content.pm.ParceledListSlice;
import android.os.Debug;
import android.os.Handler;
import android.os.Looper;
import android.os.Process;
import android.os.RemoteException;
import android.os.SystemClock;
import android.os.SystemProperties;
import android.os.UserHandle;
import android.util.Slog;

import com.android.internal.annotations.GuardedBy;
import com.android.server.am.NezhaCameraReclaimPlanner.Action;
import com.android.server.am.NezhaCameraReclaimPlanner.Candidate;
import com.android.server.am.NezhaCameraReclaimPlanner.Config;
import com.android.server.am.NezhaCameraReclaimPlanner.KillPlan;
import com.android.server.am.NezhaCameraReclaimPlanner.ReclaimPlan;
import com.android.server.am.NezhaCameraReclaimPlanner.Sample;
import com.android.server.am.NezhaCameraReclaimPlanner.State;
import com.android.server.wm.WindowProcessController;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Executes the factory CameraOpt reclaim scenes on the AOSP process list.
 *
 * The factory kills through its own lmkd command set and a MIUI process
 * service; neither exists here. This helper reads the ordinary LRU list,
 * kills through {@link ProcessRecord#killLocked}, compacts through
 * {@link CachedAppOptimizer#compactApp} and asks the cgroup v2 root for
 * proactive reclaim. Every decision comes from {@link NezhaCameraReclaimPlanner},
 * every mutation revalidates the record under the AMS lock, and the
 * configuration arrives from the factory JSON dispatcher through the service.
 */
public final class NezhaCameraReclaimPolicy {
    private static final String TAG = "NezhaCameraReclaim";
    private static final String ENABLE_PROPERTY = "ro.nezha.cameraopt.service";
    private static final String CGROUP_RECLAIM = "/sys/fs/cgroup/memory.reclaim";
    private static final String BOARD_TEMPERATURE =
            "/sys/devices/virtual/thermal/thermal_message/board_sensor_temp";
    private static final Pattern PSI_AVG10 = Pattern.compile("(?m)^some\\s+avg10=([0-9.]+)");
    private static final int MAX_RECENT_TASKS = 32;
    private static final int MAX_HISTORY = 24;
    private static final long MAX_RECLAIM_BYTES = 1L << 30;

    private final ActivityManagerService mService;
    private final Handler mHandler;
    private final Object mDispatchToken = new Object();
    private final Object mLock = new Object();
    @GuardedBy("mLock")
    private Config mConfig = Config.parse(null);
    @GuardedBy("mLock")
    private boolean mConfigured;
    @GuardedBy("mLock")
    private int mConfigUpdates;
    @GuardedBy("mLock")
    private final State mState = new State();
    @GuardedBy("mLock")
    private long mModeLevel;
    @GuardedBy("mLock")
    private boolean mClosed;
    @GuardedBy("mLock")
    private final ArrayDeque<String> mHistory = new ArrayDeque<>();
    @GuardedBy("mLock")
    private long mScenesRun;
    @GuardedBy("mLock")
    private long mKills;
    @GuardedBy("mLock")
    private long mKillsSkippedAtCommit;
    @GuardedBy("mLock")
    private long mCompactionsRequested;
    @GuardedBy("mLock")
    private long mCompactionsRefused;
    @GuardedBy("mLock")
    private long mReclaimWrites;
    @GuardedBy("mLock")
    private long mReclaimWriteFailures;
    @GuardedBy("mLock")
    private long mRateLimited;
    @GuardedBy("mLock")
    private long mUnconfigured;
    @GuardedBy("mLock")
    private long mUnknownModeLevels;
    @GuardedBy("mLock")
    private long mEscalationsSuppressed;
    @GuardedBy("mLock")
    private long mKillOnceIgnored;

    public NezhaCameraReclaimPolicy(Context context, Handler handler) {
        Objects.requireNonNull(context);
        mHandler = Objects.requireNonNull(handler);
        if (!SystemProperties.getBoolean(ENABLE_PROPERTY, false)) {
            throw new IllegalStateException("CameraOpt reclaim policy is disabled");
        }
        Object activityService = ActivityManager.getService();
        if (!(activityService instanceof ActivityManagerService)) {
            throw new IllegalStateException("CameraOpt requires the local AMS instance");
        }
        mService = (ActivityManagerService) activityService;
    }

    /** Replace the reclaim table; {@code null} clears it. Called from the JSON dispatcher path. */
    public void setConfiguration(JSONObject cameraReclaim) {
        Config config = Config.parse(cameraReclaim);
        synchronized (mLock) {
            mConfig = config;
            mConfigured = cameraReclaim != null;
            mConfigUpdates++;
            note("configuration " + (mConfigured ? "loaded" : "cleared") + ": actions="
                    + config.actionCount() + " lists=" + config.listCount() + " dropped="
                    + config.droppedEntries());
        }
    }

    /** Camera client event 3: the factory measures kill spacing from camera foreground time. */
    public void onCameraOpened(int uid, int pid) {
        synchronized (mLock) {
            mState.cameraForegroundUptime = SystemClock.uptimeMillis();
        }
    }

    /** Camera client event 4: the factory resets its mode level on close. */
    public void onCameraClosed(int uid, int pid) {
        synchronized (mLock) {
            mModeLevel = 0;
        }
    }

    /**
     * Factory {@code boostCameraByThreshold} for a nonzero level:
     * {@code ReclaimManager.boostCameraByModeLevel}. Returns false for a rejected level.
     */
    public boolean onModeLevel(int uid, int pid, long modeLevel) {
        if (modeLevel <= 0) {
            return false;
        }
        int scene = NezhaCameraReclaimPlanner.sceneForModeLevel(modeLevel);
        synchronized (mLock) {
            mModeLevel = modeLevel;
            if (!NezhaCameraReclaimPlanner.isKnownModeLevel(modeLevel)) {
                mUnknownModeLevels++;
            }
        }
        dispatch(() -> runScene(uid, pid, scene, "modeLevel=0x" + Long.toHexString(modeLevel)));
        return true;
    }

    /**
     * Factory {@code reclaimMemoryForCamera}: the capture scene, once per configured interval.
     */
    public void onCaptureReclaim(int uid, int pid, long modeId, int first, int second) {
        dispatch(() -> {
            long now = SystemClock.uptimeMillis();
            synchronized (mLock) {
                if (!NezhaCameraReclaimPlanner.captureReclaimAllowed(mConfig, mState, now)) {
                    mRateLimited++;
                    return;
                }
                mState.lastCaptureReclaimUptime = now;
            }
            runScene(uid, pid, NezhaCameraReclaimPlanner.SCENE_CAPTURE,
                    "modeId=" + modeId + " args=" + first + "," + second);
        });
    }

    public void close() {
        synchronized (mLock) {
            mClosed = true;
        }
        mHandler.removeCallbacksAndMessages(mDispatchToken);
    }

    public void dump(PrintWriter writer) {
        synchronized (mLock) {
            writer.println("camera reclaim policy: configured=" + mConfigured + " updates="
                    + mConfigUpdates + " closed=" + mClosed + " modeLevel=0x"
                    + Long.toHexString(mModeLevel) + " actions=" + mConfig.actionCount());
            writer.println("  scenes=" + mScenesRun + " kills=" + mKills
                    + " killsSkippedAtCommit=" + mKillsSkippedAtCommit
                    + " compactionsRequested=" + mCompactionsRequested
                    + " compactionsRefused=" + mCompactionsRefused
                    + " reclaimWrites=" + mReclaimWrites
                    + " reclaimWriteFailures=" + mReclaimWriteFailures
                    + " rateLimited=" + mRateLimited + " unconfigured=" + mUnconfigured
                    + " unknownModeLevels=" + mUnknownModeLevels
                    + " escalationsSuppressed=" + mEscalationsSuppressed
                    + " killOnceIgnored=" + mKillOnceIgnored
                    + " adjFloor=" + NezhaCameraReclaimPlanner.ADJ_FLOOR);
            writer.println("  lastCaptureReclaimUptimeMs=" + mState.lastCaptureReclaimUptime
                    + " lastKillBatchUptimeMs=" + mState.lastKillBatchUptime
                    + " cameraForegroundUptimeMs=" + mState.cameraForegroundUptime);
            for (String line : mHistory) {
                writer.println("  " + line);
            }
        }
    }

    private void dispatch(Runnable action) {
        Runnable guarded = () -> {
            synchronized (mLock) {
                if (mClosed) {
                    return;
                }
            }
            action.run();
        };
        if (Looper.myLooper() == mHandler.getLooper()) {
            guarded.run();
        } else if (!mHandler.postAtTime(guarded, mDispatchToken, SystemClock.uptimeMillis())) {
            Slog.w(TAG, "Reclaim handler rejected work");
        }
    }

    @GuardedBy("mLock")
    private void note(String line) {
        if (mHistory.size() >= MAX_HISTORY) {
            mHistory.removeFirst();
        }
        mHistory.addLast(SystemClock.uptimeMillis() + "ms " + line);
    }

    private void runScene(int uid, int pid, int scene, String detail) {
        final String sceneName = NezhaCameraReclaimPlanner.sceneName(scene);
        final Config config;
        synchronized (mLock) {
            if (!mConfigured || sceneName == null) {
                mUnconfigured++;
                note("scene " + scene + " ignored: " + (sceneName == null ? "unknown scene"
                        : "no configuration") + " " + detail);
                return;
            }
            config = mConfig;
            mScenesRun++;
        }
        List<Action> killActions = config.actions(NezhaCameraReclaimPlanner.ITEM_KILL_TARGET,
                sceneName);
        List<Action> reclaimActions = config.actions(NezhaCameraReclaimPlanner.ITEM_RECLAIM_ONCE,
                sceneName);
        List<Action> killOnce = config.actions(NezhaCameraReclaimPlanner.ITEM_KILL_ONCE, sceneName);
        if (!killOnce.isEmpty()) {
            synchronized (mLock) {
                // Only the factory PSI monitor scenes carry kill_once; none is reachable here.
                mKillOnceIgnored++;
            }
        }
        if (killActions.isEmpty() && reclaimActions.isEmpty()) {
            synchronized (mLock) {
                note(sceneName + ": no actions " + detail);
            }
            return;
        }
        Sample sample = sample();
        Caller caller = resolveCaller(uid);
        if (caller == null) {
            synchronized (mLock) {
                note(sceneName + ": no live camera process for uid " + uid);
            }
            return;
        }
        List<String> recents = recentTaskPackages(UserHandle.getUserId(uid));
        List<Candidate> candidates = collectCandidates();
        long now = SystemClock.uptimeMillis();
        StringBuilder summary = new StringBuilder(sceneName).append(' ').append(detail)
                .append(" sample[").append(sample).append(']');
        for (Action action : killActions) {
            if (!action.matches(sample)) {
                summary.append(" kill_target:trigger-miss");
                continue;
            }
            final KillPlan plan;
            final State stateCopy;
            synchronized (mLock) {
                stateCopy = mState;
                plan = NezhaCameraReclaimPlanner.planKill(config, scene, caller.packageName,
                        caller.uid, action, sample, candidates, recents, now, stateCopy);
                if (plan.escalationSuppressed) {
                    mEscalationsSuppressed++;
                }
            }
            summary.append(" kill_target[").append(plan).append(']');
            if (!plan.victims.isEmpty()) {
                int killed = commitKills(plan, sceneName, caller);
                synchronized (mLock) {
                    mState.lastKillBatchUptime = SystemClock.uptimeMillis();
                    mKills += killed;
                    mKillsSkippedAtCommit += plan.victims.size() - killed;
                }
                summary.append(" killed=").append(killed);
            }
        }
        for (Action action : reclaimActions) {
            if (!action.matches(sample)) {
                summary.append(" reclaim_once:trigger-miss");
                continue;
            }
            final ReclaimPlan plan;
            synchronized (mLock) {
                plan = NezhaCameraReclaimPlanner.planReclaimOnce(config, scene, caller.packageName,
                        caller.uid, action, sample, candidates, now, mState);
                if (plan.skipReason == null) {
                    mState.reclaimOnceNotBeforeUptime = now
                            + NezhaCameraReclaimPlanner.RECLAIM_ONCE_COOLDOWN_MS;
                }
            }
            summary.append(" reclaim_once[").append(plan).append(']');
            if (plan.skipReason != null) {
                continue;
            }
            boolean written = writeCgroupReclaim(plan.reclaimKb);
            summary.append(" cgroupReclaim=").append(written);
            if (plan.compactionAllowed && !plan.compactions.isEmpty()) {
                int requested = commitCompactions(plan);
                synchronized (mLock) {
                    mState.lastCompactPassUptime = SystemClock.uptimeMillis();
                }
                summary.append(" compactions=").append(requested);
            }
        }
        synchronized (mLock) {
            note(summary.toString());
        }
        Slog.i(TAG, summary.toString());
    }

    private static final class Caller {
        final int uid;
        final String packageName;

        Caller(int uid, String packageName) {
            this.uid = uid;
            this.packageName = packageName;
        }
    }

    private Caller resolveCaller(int uid) {
        final Caller[] result = new Caller[1];
        withServiceLock(() -> {
            synchronized (mService.mProcLock) {
                ProcessRecord record = mService.getProcessRecordLocked(
                        NezhaCameraReclaimPlanner.CAMERA_PACKAGE, uid);
                if (record != null && record.uid == uid && record.getThread() != null
                        && !record.isKilled()) {
                    result[0] = new Caller(uid, record.info.packageName);
                }
            }
        });
        return result[0];
    }

    private List<Candidate> collectCandidates() {
        final ArrayList<Candidate> candidates = new ArrayList<>();
        withServiceLock(() -> {
            synchronized (mService.mProcLock) {
                for (ProcessRecord record : mService.mProcessList.getLruProcessesLOSP()) {
                    if (record == null || record.info == null) {
                        continue;
                    }
                    Candidate candidate = new Candidate();
                    candidate.record = record;
                    candidate.pid = record.getPid();
                    candidate.uid = record.uid;
                    candidate.packageName = String.valueOf(record.info.packageName);
                    candidate.processName = String.valueOf(record.processName);
                    candidate.adj = record.getSetAdj();
                    candidate.procState = record.getCurProcState();
                    candidate.systemApp = record.info.isSystemApp();
                    candidate.persistent = record.isPersistent();
                    candidate.isolated = record.isolated || record.isSdkSandbox;
                    candidate.killed = record.isKilled() || record.isKilledByAm()
                            || record.getThread() == null;
                    candidate.hasForegroundServices = record.mServices.hasForegroundServices();
                    // These window-process getters are lock-free hot-path reads; the
                    // WM-locked isInterestingToUser is deliberately not used here.
                    WindowProcessController controller = record.getWindowProcessController();
                    if (controller != null) {
                        candidate.interestingToUser = controller.hasVisibleActivities()
                                || controller.isPreviousProcess();
                        candidate.home = controller.isHomeProcess();
                        candidate.heavyWeight = controller.isHeavyWeightProcess();
                        candidate.hasActivities = controller.hasActivities();
                    }
                    long pss = record.getLastPss();
                    if (pss <= 0) {
                        pss = record.getLastRss();
                    }
                    if (pss <= 0 && candidate.pid > 0) {
                        long[] rss = Process.getRss(candidate.pid);
                        pss = rss != null && rss.length > 0 ? rss[0] : 0;
                    }
                    candidate.pssKb = pss;
                    candidates.add(candidate);
                }
            }
        });
        return candidates;
    }

    /** Kill each planned victim only if it still matches what the planner saw. */
    private int commitKills(KillPlan plan, String sceneName, Caller caller) {
        final int[] killed = new int[1];
        final String reason = "nezha-cameraopt reclaim " + sceneName;
        withServiceLock(() -> {
            for (Candidate candidate : plan.victims) {
                ProcessRecord record = (ProcessRecord) candidate.record;
                boolean stillEligible;
                synchronized (mService.mProcLock) {
                    stillEligible = record.getPid() == candidate.pid && record.uid == candidate.uid
                            && record.getThread() != null && !record.isKilled()
                            && !record.isKilledByAm() && !record.isPersistent()
                            && record.uid != caller.uid
                            && !record.mServices.hasForegroundServices()
                            && record.getSetAdj() >= plan.effectiveAdjThreshold;
                }
                if (!stillEligible) {
                    continue;
                }
                WindowProcessController controller = record.getWindowProcessController();
                if (controller != null && (controller.hasVisibleActivities()
                        || controller.isPreviousProcess() || controller.isHomeProcess())) {
                    continue;
                }
                record.killLocked(reason, ApplicationExitInfo.REASON_OTHER,
                        ApplicationExitInfo.SUBREASON_MEMORY_PRESSURE, true);
                killed[0]++;
            }
        });
        return killed[0];
    }

    private int commitCompactions(ReclaimPlan plan) {
        final int[] requested = new int[1];
        final ArrayList<Integer> compacted = new ArrayList<>();
        withServiceLock(() -> {
            CachedAppOptimizer optimizer = mService.getCachedAppOptimizer();
            if (optimizer == null) {
                return;
            }
            synchronized (mService.mProcLock) {
                for (Candidate candidate : plan.compactions) {
                    ProcessRecord record = (ProcessRecord) candidate.record;
                    if (record.getPid() != candidate.pid || record.isKilled()
                            || record.getThread() == null) {
                        continue;
                    }
                    boolean queued = optimizer.compactApp(record,
                            CachedAppOptimizer.CompactProfile.FULL,
                            CachedAppOptimizer.CompactSource.APP, false);
                    if (queued) {
                        requested[0]++;
                        compacted.add(candidate.pid);
                    }
                }
            }
        });
        synchronized (mLock) {
            long now = SystemClock.uptimeMillis();
            for (Integer pid : compacted) {
                mState.compactedAtUptime.put(pid, now);
            }
            mCompactionsRequested += requested[0];
            mCompactionsRefused += plan.compactions.size() - requested[0];
        }
        return requested[0];
    }

    /** cgroup v2 proactive reclaim; the kernel may stop early and report an error. */
    private boolean writeCgroupReclaim(long kilobytes) {
        long bytes = Math.min(Math.max(kilobytes, 0) * 1024, MAX_RECLAIM_BYTES);
        if (bytes <= 0) {
            return false;
        }
        File node = new File(CGROUP_RECLAIM);
        if (!node.exists()) {
            synchronized (mLock) {
                mReclaimWriteFailures++;
            }
            return false;
        }
        try (FileOutputStream stream = new FileOutputStream(node)) {
            stream.write(Long.toString(bytes).getBytes(StandardCharsets.US_ASCII));
            synchronized (mLock) {
                mReclaimWrites++;
            }
            return true;
        } catch (IOException | SecurityException error) {
            synchronized (mLock) {
                mReclaimWriteFailures++;
            }
            return false;
        }
    }

    private Sample sample() {
        Sample sample = new Sample();
        long[] info = new long[Debug.MEMINFO_COUNT];
        Debug.getMemInfo(info);
        sample.totalKb = info[Debug.MEMINFO_TOTAL];
        sample.freeKb = info[Debug.MEMINFO_FREE];
        sample.cachedKb = info[Debug.MEMINFO_CACHED];
        sample.availableKb = info[Debug.MEMINFO_AVAILABLE];
        sample.activeFileKb = info[Debug.MEMINFO_ACTIVE_FILE];
        sample.inactiveFileKb = info[Debug.MEMINFO_INACTIVE_FILE];
        sample.fileMemKb = sample.activeFileKb + sample.inactiveFileKb;
        sample.memPsi = readPsi("/proc/pressure/memory");
        sample.cpuPsi = readPsi("/proc/pressure/cpu");
        sample.thermalC = readThermal();
        return sample;
    }

    private static String readNode(String path) {
        try (FileInputStream stream = new FileInputStream(path)) {
            byte[] buffer = new byte[1024];
            int length = stream.read(buffer);
            return length <= 0 ? "" : new String(buffer, 0, length, StandardCharsets.US_ASCII);
        } catch (IOException | SecurityException error) {
            return null;
        }
    }

    private static float readPsi(String path) {
        String text = readNode(path);
        if (text == null) {
            return -1f;
        }
        Matcher matcher = PSI_AVG10.matcher(text);
        if (!matcher.find()) {
            return -1f;
        }
        try {
            return Float.parseFloat(matcher.group(1));
        } catch (NumberFormatException error) {
            return -1f;
        }
    }

    private static float readThermal() {
        String text = readNode(BOARD_TEMPERATURE);
        if (text == null) {
            return -1f;
        }
        try {
            return Float.parseFloat(text.trim()) / 1000f;
        } catch (NumberFormatException error) {
            return -1f;
        }
    }

    private List<String> recentTaskPackages(int userId) {
        try {
            ParceledListSlice<ActivityManager.RecentTaskInfo> slice = ActivityTaskManager
                    .getService().getRecentTasks(MAX_RECENT_TASKS,
                            ActivityManager.RECENT_IGNORE_UNAVAILABLE, userId);
            if (slice == null) {
                return Collections.emptyList();
            }
            ArrayList<String> packages = new ArrayList<>();
            for (ActivityManager.RecentTaskInfo task : slice.getList()) {
                ComponentName component = task.topActivity != null ? task.topActivity
                        : task.baseActivity != null ? task.baseActivity
                        : task.baseIntent != null ? task.baseIntent.getComponent() : null;
                if (component != null && !packages.contains(component.getPackageName())) {
                    packages.add(component.getPackageName());
                }
            }
            return packages;
        } catch (RemoteException | RuntimeException error) {
            return Collections.emptyList();
        }
    }

    private void withServiceLock(Runnable action) {
        ActivityManagerService.boostPriorityForLockedSection();
        try {
            synchronized (mService) {
                action.run();
            }
        } finally {
            ActivityManagerService.resetPriorityAfterLockedSection();
        }
    }
}
