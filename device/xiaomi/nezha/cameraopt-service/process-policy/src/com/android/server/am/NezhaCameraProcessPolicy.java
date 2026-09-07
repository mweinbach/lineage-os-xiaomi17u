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

import static android.app.ActivityManagerInternal.OOM_ADJ_REASON_UI_VISIBILITY;

import android.app.ActivityManager;
import android.app.ActivityManagerInternal;
import android.app.IProcessObserver;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.os.SystemProperties;
import android.os.UserHandle;
import android.util.Slog;

import com.android.internal.annotations.GuardedBy;
import com.android.server.LocalServices;

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.Objects;

/**
 * A temporary, caller-owned camera OOM cap. Installed in services.jar so its AMS
 * access follows the same package and class-loader contract as the process code.
 *
 * This does not implement MIUI max-proc-state, memory reclaim or performance locks.
 * The ordinary max-adj value is never saved or overwritten by this helper.
 */
public final class NezhaCameraProcessPolicy {
    private static final String TAG = "NezhaCameraProcessPolicy";
    private static final String ENABLE_PROPERTY = "ro.nezha.cameraopt.service";
    private static final String CAMERA_PACKAGE = "com.android.camera";
    private static final int EVENT_CAMERA_OPEN = 3;
    private static final int EVENT_CAMERA_CLOSE = 4;

    private final ActivityManagerService mService;
    private final Handler mHandler;
    private final ActivityManagerInternal mAmInternal;
    private final Object mDispatchToken = new Object();

    @GuardedBy("mService")
    private boolean mClosed;
    @GuardedBy("mService")
    private final Map<ProcessRecord, Session> mSessions = new HashMap<>();
    @GuardedBy("mService")
    private long mNextGeneration;
    @GuardedBy("mService")
    private long mAppliedRequests;
    @GuardedBy("mService")
    private long mRejectedRequests;
    @GuardedBy("mService")
    private long mClearedContributions;

    private final IProcessObserver mProcessObserver = new IProcessObserver.Stub() {
        @Override
        public void onProcessStarted(int pid, int processUid, int packageUid,
                String packageName, String processName) {
            dispatch(() -> withServiceLock(() -> retireStaleSessionsLocked(processUid)));
        }

        @Override
        public void onForegroundActivitiesChanged(int pid, int uid, boolean foreground) {
            dispatch(() -> withServiceLock(() -> {
                Session session = currentSessionLocked(uid, pid, false);
                if (session != null) {
                    session.foregroundActivities = foreground;
                }
                // Foreground loss does not establish camera/postprocess completion.
            }));
        }

        @Override
        public void onForegroundServicesChanged(int pid, int uid, int serviceTypes) {
            dispatch(() -> withServiceLock(() -> {
                Session session = currentSessionLocked(uid, pid, false);
                if (session != null) {
                    session.foregroundServiceTypes = serviceTypes;
                }
            }));
        }

        @Override
        public void onProcessDied(int pid, int uid) {
            dispatch(() -> withServiceLock(() -> {
                // The oneway observer supplies no start sequence. Never let an old
                // PID/UID notification clear a currently live, renewed lifetime.
                Iterator<Session> it = mSessions.values().iterator();
                while (it.hasNext()) {
                    Session session = it.next();
                    if (session.pid == pid && session.uid == uid
                            && !isCurrentLifetimeLocked(session)) {
                        discardStaleSessionLocked(session);
                        it.remove();
                    }
                }
            }));
        }
    };

    public NezhaCameraProcessPolicy(Context context, Handler handler) {
        Objects.requireNonNull(context);
        mHandler = Objects.requireNonNull(handler);
        if (!SystemProperties.getBoolean(ENABLE_PROPERTY, false)) {
            throw new IllegalStateException("CameraOpt process policy is disabled");
        }
        Object activityService = ActivityManager.getService();
        if (!(activityService instanceof ActivityManagerService)) {
            throw new IllegalStateException("CameraOpt requires the local AMS instance");
        }
        mService = (ActivityManagerService) activityService;
        mAmInternal = Objects.requireNonNull(
                LocalServices.getService(ActivityManagerInternal.class),
                "ActivityManagerInternal is unavailable");
        mAmInternal.registerProcessObserver(mProcessObserver);
    }

    /**
     * Call directly at Binder entry with the captured UID/PID. Oneway Binder may
     * report PID zero; the UID authenticates the pinned camera target in that case.
     */
    public void adjBoost(int callingUid, int callingPid, String packageName, int requestedAdj,
            long durationMillis, int userId) {
        final CallerIdentity caller = captureCaller(callingUid, callingPid);
        dispatch(() -> withServiceLock(() -> {
            if (!CAMERA_PACKAGE.equals(packageName)
                    || userId != UserHandle.getUserId(callingUid)
                    || requestedAdj < 0 || requestedAdj > ProcessList.CACHED_APP_MAX_ADJ
                    || durationMillis < 0) {
                rejectLocked("invalid adjustment request");
                return;
            }
            Session session = sessionForCallerLocked(caller, true);
            if (session == null) {
                rejectLocked("caller has no matching live camera process");
                return;
            }
            cancelTimeoutLocked(session);
            session.generation = ++mNextGeneration;
            session.requestedAdj = requestedAdj;
            session.hasContribution = true;
            synchronized (mService.mProcLock) {
                session.record.setNezhaCameraMaxAdj(requestedAdj);
            }
            if (durationMillis > 0) {
                long now = SystemClock.uptimeMillis();
                session.expiresAtUptimeMillis = durationMillis > Long.MAX_VALUE - now
                        ? Long.MAX_VALUE : now + durationMillis;
                final long generation = session.generation;
                session.timeout = () -> withServiceLock(() -> {
                    if (!mClosed && mSessions.get(session.record) == session
                            && session.generation == generation) {
                        clearContributionLocked(session, "timeout");
                    }
                });
                if (!mHandler.postAtTime(session.timeout, mDispatchToken,
                        session.expiresAtUptimeMillis)) {
                    clearContributionLocked(session, "timeout scheduling failed");
                    rejectLocked("cannot schedule adjustment expiry");
                    return;
                }
            }
            mAppliedRequests++;
            // This may enqueue a batch update. The contribution remains valid in
            // either case; no claim about a measured kernel OOM score is made.
            mService.updateOomAdjLocked(session.record, OOM_ADJ_REASON_UI_VISIBILITY);
        }));
    }

    public void onCameraEvent(int uid, int pid, int event, String payload) {
        if (event != EVENT_CAMERA_OPEN && event != EVENT_CAMERA_CLOSE) {
            return;
        }
        final CallerIdentity caller = captureCaller(uid, pid);
        dispatch(() -> withServiceLock(() -> {
            Session session = sessionForCallerLocked(caller, event == EVENT_CAMERA_OPEN);
            if (session == null) {
                return;
            }
            session.cameraOpen = event == EVENT_CAMERA_OPEN;
            if (!session.cameraOpen) {
                clearContributionLocked(session, "camera close");
            }
        }));
    }

    public void onPostProcessComplete(int uid, int pid) {
        final CallerIdentity caller = captureCaller(uid, pid);
        dispatch(() -> withServiceLock(() -> {
            Session session = sessionForCallerLocked(caller, false);
            if (session != null && !session.cameraOpen) {
                clearContributionLocked(session, "postprocess complete after close");
            }
        }));
    }

    /** Roll back publication/startup failure without leaving caps or observer work behind. */
    public void close() {
        final boolean[] unregister = new boolean[1];
        withServiceLock(() -> {
            if (mClosed) {
                return;
            }
            mClosed = true;
            for (Session session : new ArrayList<>(mSessions.values())) {
                clearContributionLocked(session, "policy close");
            }
            mSessions.clear();
            unregister[0] = true;
        });
        if (unregister[0]) {
            mHandler.removeCallbacksAndMessages(mDispatchToken);
            mAmInternal.unregisterProcessObserver(mProcessObserver);
        }
    }

    public void dump(PrintWriter writer) {
        ArrayList<String> lines = new ArrayList<>();
        withServiceLock(() -> {
            lines.add("camera process policy: enabled=true closed=" + mClosed
                    + " applied=" + mAppliedRequests
                    + " rejected=" + mRejectedRequests + " cleared=" + mClearedContributions);
            for (Session session : mSessions.values()) {
                lines.add("  uid=" + session.uid + " pid=" + session.pid
                        + " startSeq=" + session.startSeq + " generation=" + session.generation
                        + " cameraOpen=" + session.cameraOpen
                        + " foregroundActivities=" + session.foregroundActivities
                        + " foregroundServiceTypes=" + session.foregroundServiceTypes
                        + " active=" + session.hasContribution
                        + " requestedAdj=" + session.requestedAdj
                        + " baseMaxAdj=" + session.record.getNezhaCameraBaseMaxAdj()
                        + " effectiveMaxAdj=" + session.record.getMaxAdj()
                        + " expiresAtUptimeMs=" + session.expiresAtUptimeMillis);
            }
        });
        for (String line : lines) {
            writer.println(line);
        }
    }

    private void dispatch(Runnable action) {
        Runnable guarded = () -> withServiceLock(() -> {
            if (!mClosed) {
                action.run();
            }
        });
        if (Looper.myLooper() == mHandler.getLooper()) {
            guarded.run();
        } else if (!mHandler.postAtTime(guarded, mDispatchToken, SystemClock.uptimeMillis())) {
            Slog.w(TAG, "Process-policy handler rejected work");
        }
    }

    private CallerIdentity captureCaller(int uid, int reportedPid) {
        final CallerIdentity[] result = new CallerIdentity[1];
        withServiceLock(() -> {
            if (mClosed || reportedPid < 0) {
                return;
            }
            synchronized (mService.mProcLock) {
                ProcessRecord record = mService.getProcessRecordLocked(CAMERA_PACKAGE, uid);
                if (record == null) {
                    return;
                }
                int actualPid = record.getPid();
                if ((reportedPid != 0 && reportedPid != actualPid)
                        || !isCallerOwnedLocked(record, uid, actualPid)) {
                    return;
                }
                result[0] = new CallerIdentity(record, uid, actualPid, record.getStartSeq());
            }
        });
        return result[0];
    }

    @GuardedBy("mService")
    private Session sessionForCallerLocked(CallerIdentity caller, boolean create) {
        if (caller == null) {
            return null;
        }
        retireStaleSessionsLocked(caller.uid);
        synchronized (mService.mProcLock) {
            if (mService.getProcessRecordLocked(CAMERA_PACKAGE, caller.uid) != caller.record
                    || !isCallerOwnedLocked(caller.record, caller.uid, caller.pid)
                    || caller.record.getStartSeq() != caller.startSeq) {
                return null;
            }
        }
        Session session = mSessions.get(caller.record);
        if (session == null && create) {
            session = new Session(caller.record, caller.uid, caller.pid, caller.startSeq);
            mSessions.put(caller.record, session);
        }
        return session;
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

    @GuardedBy("mService")
    private Session currentSessionLocked(int uid, int pid, boolean create) {
        retireStaleSessionsLocked(uid);
        ProcessRecord record;
        long startSeq;
        synchronized (mService.mProcLock) {
            record = mService.getProcessRecordLocked(CAMERA_PACKAGE, uid);
            if (!isCallerOwnedLocked(record, uid, pid)) {
                return null;
            }
            startSeq = record.getStartSeq();
        }
        Session session = mSessions.get(record);
        if (session == null && create) {
            session = new Session(record, uid, pid, startSeq);
            mSessions.put(record, session);
        }
        return session;
    }

    @GuardedBy({"mService", "mService.mProcLock"})
    private boolean isCallerOwnedLocked(ProcessRecord record, int uid, int pid) {
        return record != null && pid > 0 && record.uid == uid && record.getPid() == pid
                && record.info.uid == uid && CAMERA_PACKAGE.equals(record.info.packageName)
                && CAMERA_PACKAGE.equals(record.processName)
                && !record.isKilled() && !record.isKilledByAm() && record.getThread() != null;
    }

    @GuardedBy("mService")
    private boolean isCurrentLifetimeLocked(Session session) {
        synchronized (mService.mProcLock) {
            return mService.getProcessRecordLocked(CAMERA_PACKAGE, session.uid) == session.record
                    && isCallerOwnedLocked(session.record, session.uid, session.pid)
                    && session.record.getStartSeq() == session.startSeq;
        }
    }

    @GuardedBy("mService")
    private void retireStaleSessionsLocked(int uid) {
        Iterator<Session> it = mSessions.values().iterator();
        while (it.hasNext()) {
            Session session = it.next();
            if (session.uid == uid && !isCurrentLifetimeLocked(session)) {
                discardStaleSessionLocked(session);
                it.remove();
            }
        }
    }

    @GuardedBy("mService")
    private void discardStaleSessionLocked(Session session) {
        cancelTimeoutLocked(session);
        // Intrinsic killed/cleanup hooks already remove a dead lifetime's cap.
        // Never clear a record reused for a newer start sequence.
        synchronized (mService.mProcLock) {
            if (session.record.getPid() == session.pid
                    && session.record.getStartSeq() == session.startSeq) {
                session.record.clearNezhaCameraMaxAdj();
            }
        }
        session.hasContribution = false;
    }

    @GuardedBy("mService")
    private void clearContributionLocked(Session session, String reason) {
        cancelTimeoutLocked(session);
        if (!session.hasContribution) {
            return;
        }
        boolean current = isCurrentLifetimeLocked(session);
        if (current) {
            synchronized (mService.mProcLock) {
                session.record.clearNezhaCameraMaxAdj();
            }
            mService.updateOomAdjLocked(session.record, OOM_ADJ_REASON_UI_VISIBILITY);
        } else {
            discardStaleSessionLocked(session);
            mSessions.remove(session.record, session);
        }
        session.hasContribution = false;
        mClearedContributions++;
        Slog.d(TAG, "Cleared camera cap for uid=" + session.uid + " pid=" + session.pid
                + " reason=" + reason);
    }

    @GuardedBy("mService")
    private void cancelTimeoutLocked(Session session) {
        if (session.timeout != null) {
            mHandler.removeCallbacks(session.timeout);
            session.timeout = null;
        }
        session.expiresAtUptimeMillis = 0;
    }

    @GuardedBy("mService")
    private void rejectLocked(String reason) {
        mRejectedRequests++;
        Slog.w(TAG, "Rejected camera cap: " + reason);
    }

    private static final class Session {
        final ProcessRecord record;
        final int uid;
        final int pid;
        final long startSeq;
        long generation;
        long expiresAtUptimeMillis;
        int requestedAdj;
        boolean hasContribution;
        boolean cameraOpen;
        boolean foregroundActivities;
        int foregroundServiceTypes;
        Runnable timeout;

        Session(ProcessRecord record, int uid, int pid, long startSeq) {
            this.record = record;
            this.uid = uid;
            this.pid = pid;
            this.startSeq = startSeq;
        }
    }

    private static final class CallerIdentity {
        final ProcessRecord record;
        final int uid;
        final int pid;
        final long startSeq;

        CallerIdentity(ProcessRecord record, int uid, int pid, long startSeq) {
            this.record = record;
            this.uid = uid;
            this.pid = pid;
            this.startSeq = startSeq;
        }
    }
}
