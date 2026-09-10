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

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Decision logic for the factory CameraOpt "CameraReclaim" tables.
 *
 * This class holds no Android service reference. It parses the reclaim
 * configuration the way the factory {@code ReclaimJsonParser} and
 * {@code ReclaimActions} classes do, evaluates the same trigger conditions,
 * and orders kill and compaction candidates the way the factory
 * {@code KillTargetAction}, {@code ProcessClassfier} and
 * {@code ProcCompactAction} classes do. Where this build cannot reproduce a
 * factory mechanism, the deviation is named in the plan so dumps and records
 * can show it. The class is deliberately free of process-list access so a
 * host JVM can exercise it with synthetic candidates.
 */
public final class NezhaCameraReclaimPlanner {
    public static final String CAMERA_PACKAGE = "com.android.camera";

    /** Action items from the factory reclaim table. */
    public static final String ITEM_KILL_TARGET = "kill_target";
    public static final String ITEM_RECLAIM_ONCE = "reclaim_once";
    public static final String ITEM_KILL_ONCE = "kill_once";

    /** Scene identifiers and names from the factory {@code ReclaimManager} map. */
    public static final int SCENE_CAPTURE = 9;
    public static final int SCENE_VIDEO_SWITCH = 11;
    public static final int SCENE_LIVE_MOTION = 12;
    public static final int SCENE_200M = 14;
    public static final int SCENE_VIDEO_4K_DOLBY = 16;

    /** Mode levels the camera application passes to boostCameraByThreshold. */
    public static final long MODE_VIDEO_4K = 0x101;
    public static final long MODE_VIDEO_8K = 0x102;
    public static final long MODE_VIDEO_4K_DOLBY = 0x103;
    public static final long MODE_200M = 0x201;
    public static final long MODE_MASTER_LIVE = 0x202;

    /**
     * Authored floor. The factory lowers its kill threshold to zero when
     * MemFree drops under a configured value; on this build MemFree is
     * usually low because the factory memory daemons are absent, so that
     * escalation would reach visible and perceptible processes on nearly
     * every capture. Kills never go below the factory's nominal service-B band.
     */
    public static final int ADJ_FLOOR = ProcessList.SERVICE_B_ADJ;
    /** Authored bounds; the factory has none beyond its memory gap. */
    public static final int MAX_KILLS_PER_BATCH = 8;
    public static final int MAX_COMPACTIONS_PER_PASS = 16;
    public static final int MAX_RECENT_PROTECT = 8;

    /** Factory defaults used when the table omits a key. */
    public static final long DEFAULT_CAPTURE_INTERVAL_MS = 60000;
    public static final long DEFAULT_KILL_START_MS = 2000;
    public static final long DEFAULT_RESTART_KILL_MS = 1500;
    public static final long DEFAULT_ADJ_THRESHOLD = 800;
    public static final long DEFAULT_LOW_ADJ_THRESHOLD = 701;
    public static final long DEFAULT_SKIP_TASK = 4;
    public static final long DEFAULT_SKIP_TASK_LOWER = 2;
    public static final long DEFAULT_LOW_FREE_KB = 153600;
    public static final long DEFAULT_COMPACT_FREE_KB = 153600;
    public static final long DEFAULT_CAMERA_THERMAL_C = 46;
    public static final long DEFAULT_COMPACT_THERMAL_C = 46;
    public static final long DEFAULT_MAX_CPU_PSI = 70;
    public static final long RECLAIM_ONCE_COOLDOWN_MS = 2000;
    public static final long COMPACT_PASS_INTERVAL_MS = 5000;
    public static final long COMPACT_PROCESS_INTERVAL_MS = 30000;

    /** Process buckets in the factory's kill order (bit values are the factory's). */
    public static final int BUCKET_THIRD_PARTY = 1;
    public static final int BUCKET_SYSTEM = 2;
    public static final int BUCKET_PROTECT = 4;
    public static final int BUCKET_PERCEPTIBLE = 8;
    public static final int BUCKET_LIGHT_WHITE = 16;
    public static final int BUCKET_WHITE = 32;

    private static final int MAX_LIST_ENTRIES = 512;
    private static final int MAX_ACTIONS = 256;
    private static final int MAX_NAME_CHARS = 256;

    private NezhaCameraReclaimPlanner() {
    }

    /** Factory {@code ReclaimManager.boostCameraByModeLevel} scene selection. */
    public static int sceneForModeLevel(long modeLevel) {
        if (modeLevel == MODE_VIDEO_4K_DOLBY) {
            return SCENE_VIDEO_4K_DOLBY;
        }
        if (modeLevel == MODE_200M) {
            return SCENE_200M;
        }
        if (modeLevel == MODE_MASTER_LIVE) {
            return SCENE_LIVE_MOTION;
        }
        // 4K, 8K and every unknown positive level select the video switch scene.
        return SCENE_VIDEO_SWITCH;
    }

    public static boolean isKnownModeLevel(long modeLevel) {
        return modeLevel == MODE_VIDEO_4K || modeLevel == MODE_VIDEO_8K
                || modeLevel == MODE_VIDEO_4K_DOLBY || modeLevel == MODE_200M
                || modeLevel == MODE_MASTER_LIVE;
    }

    public static String sceneName(int scene) {
        switch (scene) {
            case SCENE_CAPTURE: return "miuicam_capture_event";
            case SCENE_VIDEO_SWITCH: return "miuicam_video_switch_event";
            case SCENE_LIVE_MOTION: return "live_motion_scene_event";
            case SCENE_200M: return "200M_scene_event";
            case SCENE_VIDEO_4K_DOLBY: return "video_4k_dolby_event";
            default: return null;
        }
    }

    /** One trigger range: value must be strictly above low and strictly below high. */
    public static final class Condition {
        public final String type;
        public final long low;
        public final long high;

        Condition(String type, long low, long high) {
            this.type = type;
            this.low = low;
            this.high = high;
        }

        /** Factory {@code ReclaimActions$Condition.b}: "low:high", high -1 means unbounded. */
        static Condition parse(String type, String range) {
            if (range == null) {
                return null;
            }
            String[] parts = range.split(":");
            if (parts.length != 2) {
                return null;
            }
            try {
                long low = Long.parseLong(parts[0].trim());
                long high = Long.parseLong(parts[1].trim());
                if (high == -1) {
                    high = Integer.MAX_VALUE;
                }
                return new Condition(type, low, high);
            } catch (NumberFormatException error) {
                return null;
            }
        }

        boolean matches(Sample sample) {
            final double value;
            switch (type) {
                case "free": value = sample.freeKb; break;
                case "cache": value = sample.cachedKb; break;
                case "some_mem_psi": value = sample.memPsi; break;
                case "cpu_psi": value = sample.cpuPsi; break;
                case "availablemem": value = sample.availableKb; break;
                default: value = 0; break;
            }
            return value > low && value < high;
        }

        @Override
        public String toString() {
            return type + "(" + low + "," + high + ")";
        }
    }

    /** One entry of an action list in the factory table. */
    public static final class Action {
        public final boolean enabled;
        public final long target;
        public final long freeTarget;
        public final long cpuPsiTarget;
        public final int killLevel;
        public final List<Condition> triggers;

        Action(boolean enabled, long target, long freeTarget, long cpuPsiTarget, int killLevel,
                List<Condition> triggers) {
            this.enabled = enabled;
            this.target = target;
            this.freeTarget = freeTarget;
            this.cpuPsiTarget = cpuPsiTarget;
            this.killLevel = killLevel;
            this.triggers = Collections.unmodifiableList(triggers);
        }

        /** Factory {@code ReclaimActions$Action.a}: disabled never matches; all triggers must hold. */
        public boolean matches(Sample sample) {
            if (!enabled) {
                return false;
            }
            for (Condition condition : triggers) {
                if (!condition.matches(sample)) {
                    return false;
                }
            }
            return true;
        }

        @Override
        public String toString() {
            return "enabled=" + enabled + " target=" + target + " freeTarget=" + freeTarget
                    + " cpuPsiTarget=" + cpuPsiTarget + " killLevel=" + killLevel
                    + " triggers=" + triggers;
        }
    }

    /** Parsed "CameraReclaim" section. Unknown keys are ignored, sizes are bounded. */
    public static final class Config {
        private final Map<String, Boolean> mSupport = new HashMap<>();
        private final Map<String, Long> mThreshold = new HashMap<>();
        private final Map<String, Long> mCaptureThreshold = new HashMap<>();
        private final Map<String, List<String>> mLists = new HashMap<>();
        private final Map<String, Long> mKillPssThreshold = new HashMap<>();
        private final Map<String, Long> mKillAdjThreshold = new HashMap<>();
        private final Map<String, Map<String, List<Action>>> mActions = new LinkedHashMap<>();
        private int mActionCount;
        private int mDroppedEntries;

        public static Config parse(JSONObject cameraReclaim) {
            Config config = new Config();
            if (cameraReclaim == null) {
                return config;
            }
            config.parseTyped(cameraReclaim.optJSONObject("support"), config.mSupport, null);
            config.parseTyped(cameraReclaim.optJSONObject("threshold"), null, config.mThreshold);
            config.parseTyped(cameraReclaim.optJSONObject("capture_threshold"), null,
                    config.mCaptureThreshold);
            config.parseLists(cameraReclaim.optJSONArray("configs"));
            config.parseKillConfigs(cameraReclaim.optJSONArray("kill_configs"));
            config.parseActions(cameraReclaim.optJSONObject("ReclaimActions"));
            return config;
        }

        private void parseTyped(JSONObject object, Map<String, Boolean> booleans,
                Map<String, Long> longs) {
            if (object == null) {
                return;
            }
            Iterator<String> keys = object.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                if (key == null || key.length() > MAX_NAME_CHARS) {
                    mDroppedEntries++;
                    continue;
                }
                if (booleans != null) {
                    booleans.put(key, object.optBoolean(key, false));
                } else {
                    longs.put(key, object.optLong(key, 0));
                }
            }
        }

        /** Factory {@code ReclaimJsonParser.l}: [{"name": ..., "config": [...]}]. */
        private void parseLists(JSONArray array) {
            if (array == null) {
                return;
            }
            for (int i = 0; i < array.length(); i++) {
                JSONObject entry = array.optJSONObject(i);
                if (entry == null) {
                    continue;
                }
                String name = entry.optString("name", "");
                JSONArray values = entry.optJSONArray("config");
                if (name.isEmpty() || name.length() > MAX_NAME_CHARS || values == null) {
                    mDroppedEntries++;
                    continue;
                }
                ArrayList<String> list = new ArrayList<>();
                for (int j = 0; j < values.length() && list.size() < MAX_LIST_ENTRIES; j++) {
                    String value = values.optString(j, "");
                    if (!value.isEmpty() && value.length() <= MAX_NAME_CHARS) {
                        list.add(value);
                    }
                }
                mLists.put(name, Collections.unmodifiableList(list));
            }
        }

        /** Factory {@code ReclaimJsonParser.m}: per-process PSS and adjustment thresholds. */
        private void parseKillConfigs(JSONArray array) {
            if (array == null) {
                return;
            }
            for (int i = 0; i < array.length(); i++) {
                JSONObject entry = array.optJSONObject(i);
                if (entry == null) {
                    continue;
                }
                String name = entry.optString("name", "");
                JSONObject values = entry.optJSONObject("config");
                if (values == null) {
                    continue;
                }
                Map<String, Long> destination;
                if ("pss_threshold".equals(name)) {
                    destination = mKillPssThreshold;
                } else if ("adj_threshold".equals(name)) {
                    destination = mKillAdjThreshold;
                } else {
                    continue;
                }
                Iterator<String> keys = values.keys();
                while (keys.hasNext() && destination.size() < MAX_LIST_ENTRIES) {
                    String key = keys.next();
                    if (key != null && key.length() <= MAX_NAME_CHARS) {
                        destination.put(key, values.optLong(key, 0));
                    }
                }
            }
        }

        /** Factory {@code ReclaimActions.d}: item -> scene -> [action]. */
        private void parseActions(JSONObject items) {
            if (items == null) {
                return;
            }
            for (String item : new String[] {ITEM_KILL_ONCE, ITEM_KILL_TARGET, ITEM_RECLAIM_ONCE}) {
                JSONObject scenes = items.optJSONObject(item);
                if (scenes == null) {
                    continue;
                }
                Map<String, List<Action>> byScene = new LinkedHashMap<>();
                Iterator<String> sceneNames = scenes.keys();
                while (sceneNames.hasNext()) {
                    String scene = sceneNames.next();
                    JSONArray actions = scenes.optJSONArray(scene);
                    if (scene == null || scene.length() > MAX_NAME_CHARS || actions == null) {
                        mDroppedEntries++;
                        continue;
                    }
                    ArrayList<Action> list = new ArrayList<>();
                    for (int i = 0; i < actions.length(); i++) {
                        JSONObject action = actions.optJSONObject(i);
                        if (action == null || mActionCount >= MAX_ACTIONS) {
                            mDroppedEntries++;
                            continue;
                        }
                        ArrayList<Condition> triggers = new ArrayList<>();
                        JSONObject trigger = action.optJSONObject("trigger");
                        if (trigger != null) {
                            Iterator<String> types = trigger.keys();
                            while (types.hasNext()) {
                                String type = types.next();
                                Condition condition = Condition.parse(type,
                                        trigger.optString(type, null));
                                if (condition != null) {
                                    triggers.add(condition);
                                } else {
                                    mDroppedEntries++;
                                }
                            }
                        }
                        // The table mixes numbers and numeric strings; optLong reads both.
                        list.add(new Action(action.optBoolean("enable", false),
                                action.optLong("target", 0), action.optLong("free_target", 0),
                                action.optLong("cpu_psi_target", 0), action.optInt("kill_level", 0),
                                triggers));
                        mActionCount++;
                    }
                    byScene.put(scene, Collections.unmodifiableList(list));
                }
                mActions.put(item, byScene);
            }
        }

        public boolean support(String name) {
            Boolean value = mSupport.get(name);
            return value != null && value;
        }

        public long threshold(String name, long fallback) {
            Long value = mThreshold.get(name);
            return value == null ? fallback : value;
        }

        public long captureThreshold(String name, long fallback) {
            Long value = mCaptureThreshold.get(name);
            return value == null ? fallback : value;
        }

        public List<String> list(String name) {
            List<String> value = mLists.get(name);
            return value == null ? Collections.emptyList() : value;
        }

        public long killPssThreshold(String processName) {
            Long value = mKillPssThreshold.get(processName);
            return value == null ? 0 : value;
        }

        public long killAdjThreshold(String processName) {
            Long value = mKillAdjThreshold.get(processName);
            return value == null ? 0 : value;
        }

        public List<Action> actions(String item, String scene) {
            Map<String, List<Action>> byScene = mActions.get(item);
            if (byScene == null) {
                return Collections.emptyList();
            }
            List<Action> list = byScene.get(scene);
            return list == null ? Collections.emptyList() : list;
        }

        public int actionCount() {
            return mActionCount;
        }

        public int droppedEntries() {
            return mDroppedEntries;
        }

        public int listCount() {
            return mLists.size();
        }

        public String describe() {
            StringBuilder builder = new StringBuilder();
            for (Map.Entry<String, Map<String, List<Action>>> item : mActions.entrySet()) {
                for (Map.Entry<String, List<Action>> scene : item.getValue().entrySet()) {
                    builder.append("  ").append(item.getKey()).append('/').append(scene.getKey())
                            .append(": ").append(scene.getValue()).append('\n');
                }
            }
            return builder.toString();
        }
    }

    /** Memory and pressure sample in the factory's units (kB, percent, degrees). */
    public static final class Sample {
        public long totalKb;
        public long freeKb;
        public long cachedKb;
        public long availableKb;
        public long activeFileKb;
        public long inactiveFileKb;
        public long fileMemKb;
        public float memPsi = -1f;
        public float cpuPsi = -1f;
        public float thermalC = -1f;

        @Override
        public String toString() {
            return "total=" + totalKb + " free=" + freeKb + " cached=" + cachedKb
                    + " available=" + availableKb + " file=" + fileMemKb + " memPsi=" + memPsi
                    + " cpuPsi=" + cpuPsi + " thermal=" + thermalC;
        }
    }

    /** What the planner needs to know about one process. Built by the policy under AMS locks. */
    public static final class Candidate {
        public int pid;
        public int uid;
        public int adj;
        public int procState;
        public String packageName;
        public String processName;
        public long pssKb;
        public boolean systemApp;
        public boolean persistent;
        public boolean hasForegroundServices;
        public boolean interestingToUser;
        public boolean home;
        public boolean heavyWeight;
        public boolean hasActivities;
        public boolean isolated;
        public boolean killed;
        public int bucket;
        public String skip;
        /** Opaque handle for the caller (the ProcessRecord); never inspected here. */
        public Object record;

        @Override
        public String toString() {
            return processName + "/" + uid + " pid=" + pid + " adj=" + adj + " pss=" + pssKb
                    + " bucket=" + bucket + (skip != null ? " skip=" + skip : "");
        }
    }

    /** Timing state the policy keeps across calls. */
    public static final class State {
        public long lastKillBatchUptime;
        public long cameraForegroundUptime;
        public long lastCaptureReclaimUptime;
        public long reclaimOnceNotBeforeUptime;
        public long lastCompactPassUptime;
        public final Map<Integer, Long> compactedAtUptime = new HashMap<>();
    }

    public static final class KillPlan {
        public String skipReason;
        public long nominalAdjThreshold;
        public long factoryAdjThreshold;
        public int effectiveAdjThreshold;
        public boolean escalationSuppressed;
        public long gapKb;
        public long plannedKb;
        public int belowFloor;
        public int excluded;
        public final List<Candidate> victims = new ArrayList<>();

        @Override
        public String toString() {
            return "skip=" + skipReason + " gapKb=" + gapKb + " adj=" + effectiveAdjThreshold
                    + " (nominal " + nominalAdjThreshold + ", factory " + factoryAdjThreshold
                    + (escalationSuppressed ? ", escalation suppressed" : "") + ") victims="
                    + victims.size() + " plannedKb=" + plannedKb + " belowFloor=" + belowFloor
                    + " excluded=" + excluded;
        }
    }

    public static final class ReclaimPlan {
        public String skipReason;
        public long reclaimKb;
        public boolean compactionAllowed;
        public String compactionSkipReason;
        public final List<Candidate> compactions = new ArrayList<>();

        @Override
        public String toString() {
            return "skip=" + skipReason + " reclaimKb=" + reclaimKb + " compaction="
                    + compactionAllowed + " compactionSkip=" + compactionSkipReason
                    + " compactions=" + compactions.size();
        }
    }

    /** Factory {@code ReclaimManager.notifyCameraStatusChanged(9, ...)} rate limit. */
    public static boolean captureReclaimAllowed(Config config, State state, long nowUptime) {
        long interval = config.threshold("duration_reclaim_capture", DEFAULT_CAPTURE_INTERVAL_MS);
        return nowUptime - state.lastCaptureReclaimUptime >= interval;
    }

    /**
     * Factory {@code KillTargetAction.a/b/l/o/k} and {@code ProcessClassfier}, with the
     * authored floor and bounds. {@code recents} lists recent task packages, most recent first.
     */
    public static KillPlan planKill(Config config, int scene, String callerPackage, int callerUid,
            Action action, Sample sample, List<Candidate> candidates, List<String> recents,
            long nowUptime, State state) {
        KillPlan plan = new KillPlan();
        final boolean miuiCamera = CAMERA_PACKAGE.equals(callerPackage);
        if (action.target < 0) {
            plan.skipReason = "invalid target";
            return plan;
        }
        long killStart = config.threshold("kill_start_duration", DEFAULT_KILL_START_MS);
        long restartKill = config.threshold("restart_kill_duration", DEFAULT_RESTART_KILL_MS);
        if (nowUptime - state.lastKillBatchUptime < killStart) {
            plan.skipReason = "kill batch interval";
            return plan;
        }
        if (nowUptime - state.cameraForegroundUptime < restartKill) {
            plan.skipReason = "camera restart interval";
            return plan;
        }

        // Factory getKillParams.
        plan.nominalAdjThreshold = config.threshold("adj_threshold", DEFAULT_ADJ_THRESHOLD);
        plan.factoryAdjThreshold = plan.nominalAdjThreshold;
        if (sample.freeKb < config.threshold("lowerAdj_freeMem_threshold", 0)) {
            plan.factoryAdjThreshold = config.threshold(
                    miuiCamera ? "lowAdj_threshold" : "3rd_lowAdj_threshold",
                    DEFAULT_LOW_ADJ_THRESHOLD);
        }
        long effective = Math.max(plan.factoryAdjThreshold, ADJ_FLOOR);
        plan.escalationSuppressed = plan.factoryAdjThreshold < effective;
        plan.effectiveAdjThreshold = (int) Math.min(effective, ProcessList.CACHED_APP_MAX_ADJ);
        long quarter = sample.totalKb / 4;
        long gap = Math.max(quarter - sample.availableKb, action.freeTarget - sample.freeKb);
        if (miuiCamera) {
            gap = Math.max(gap, config.threshold("free_memory_threshold", 0) - sample.freeKb);
        }
        plan.gapKb = gap;
        if (gap <= 0) {
            plan.skipReason = "no memory gap";
            return plan;
        }

        // Factory ProcessClassfier.c: recent tasks become light-white or protected.
        long skipTask = config.threshold("skip_task", DEFAULT_SKIP_TASK);
        if (sample.freeKb < config.threshold("lowerAdj_freeMem_threshold", 0)) {
            skipTask = config.threshold(miuiCamera ? "skip_task_lower" : "3rd_skip_task_lower",
                    DEFAULT_SKIP_TASK_LOWER);
        }
        ArrayList<String> recentLight = new ArrayList<>();
        ArrayList<String> recentProtect = new ArrayList<>();
        List<String> white = config.list("white_list");
        List<String> lightWhite = config.list("light_white_list");
        List<String> perceptible = config.list("perceptible_list");
        List<String> protect = config.list("protect_list");
        List<String> dynamicProtect = config.list("dynamic_protect_list");
        int position = 0;
        for (String recent : recents) {
            if (recent == null || recent.equals(callerPackage)) {
                continue;
            }
            if (position < skipTask) {
                recentLight.add(recent);
            } else if (recentProtect.size() < MAX_RECENT_PROTECT
                    && (protect.contains(recent) || perceptible.contains(recent)
                    || lightWhite.contains(recent) || white.contains(recent))) {
                recentProtect.add(recent);
            }
            position++;
        }

        // Factory KillTargetAction.o: classify every live process into a bucket.
        ArrayList<Candidate> thirdParty = new ArrayList<>();
        ArrayList<Candidate> system = new ArrayList<>();
        ArrayList<Candidate> protectBucket = new ArrayList<>();
        ArrayList<Candidate> perceptibleBucket = new ArrayList<>();
        ArrayList<Candidate> lightBucket = new ArrayList<>();
        ArrayList<Candidate> whiteBucket = new ArrayList<>();
        for (Candidate candidate : candidates) {
            String exclusion = exclusionReason(candidate, callerPackage, callerUid);
            if (exclusion != null) {
                candidate.skip = exclusion;
                plan.excluded++;
                continue;
            }
            if (candidate.adj < plan.effectiveAdjThreshold) {
                candidate.skip = "below adj threshold";
                plan.belowFloor++;
                continue;
            }
            if (white.contains(candidate.processName)) {
                candidate.bucket = BUCKET_WHITE;
                whiteBucket.add(candidate);
            } else if (lightWhite.contains(candidate.processName)
                    || (recentLight.contains(candidate.packageName)
                    && isLightWhiteRecent(candidate, dynamicProtect))) {
                candidate.bucket = BUCKET_LIGHT_WHITE;
                lightBucket.add(candidate);
            } else if (perceptible.contains(candidate.processName)
                    || candidate.adj <= ProcessList.PERCEPTIBLE_APP_ADJ) {
                candidate.bucket = BUCKET_PERCEPTIBLE;
                perceptibleBucket.add(candidate);
            } else if (protect.contains(candidate.processName)
                    || recentProtect.contains(candidate.packageName)) {
                candidate.bucket = BUCKET_PROTECT;
                protectBucket.add(candidate);
            } else if (candidate.systemApp) {
                candidate.bucket = BUCKET_SYSTEM;
                system.add(candidate);
            } else {
                candidate.bucket = BUCKET_THIRD_PARTY;
                thirdParty.add(candidate);
            }
        }

        // Factory KillTargetAction.k: third-party and qualifying system processes first.
        long killTag = config.threshold(miuiCamera ? "kill_tag" : "3rd_kill_tag", 1);
        long highPrioSystemKb = config.threshold("kill_highprio_sysapp_threshlod", 0);
        long lowPrioSystemKb = config.threshold("kill_lowprio_sysapp_threshlod", 0);
        ArrayList<Candidate> first = new ArrayList<>();
        if ((killTag & BUCKET_THIRD_PARTY) != 0) {
            first.addAll(thirdParty);
        }
        if ((killTag & BUCKET_SYSTEM) != 0) {
            for (Candidate candidate : system) {
                long minimum = candidate.adj > ProcessList.PERCEPTIBLE_APP_ADJ
                        ? highPrioSystemKb : lowPrioSystemKb;
                if (candidate.pssKb >= minimum) {
                    first.add(candidate);
                }
            }
        }
        Collections.sort(first, new RecentOrder(recents));
        long planned = 0;
        for (Candidate candidate : first) {
            if (planned >= gap || plan.victims.size() >= MAX_KILLS_PER_BATCH) {
                break;
            }
            if (candidate.pssKb > 0) {
                plan.victims.add(candidate);
                planned += candidate.pssKb;
            }
        }
        if (planned < gap && plan.victims.size() < MAX_KILLS_PER_BATCH) {
            ArrayList<Candidate> second = new ArrayList<>();
            if ((killTag & BUCKET_PROTECT) != 0) {
                second.addAll(protectBucket);
            }
            if ((killTag & BUCKET_PERCEPTIBLE) != 0) {
                second.addAll(perceptibleBucket);
            }
            // Factory getKilledWeightProcess: white processes only beyond their own thresholds.
            for (ArrayList<Candidate> bucket : Arrays2.of(lightBucket, whiteBucket)) {
                int bit = bucket == lightBucket ? BUCKET_LIGHT_WHITE : BUCKET_WHITE;
                if ((killTag & bit) == 0) {
                    continue;
                }
                for (Candidate candidate : bucket) {
                    long pssThreshold = config.killPssThreshold(candidate.processName);
                    long adjThreshold = config.killAdjThreshold(candidate.processName);
                    if (pssThreshold > 0 && candidate.pssKb > pssThreshold
                            && candidate.adj > adjThreshold) {
                        second.add(candidate);
                    }
                }
            }
            Collections.sort(second, new RecentOrder(recents));
            for (Candidate candidate : second) {
                if (planned >= gap || plan.victims.size() >= MAX_KILLS_PER_BATCH) {
                    break;
                }
                if (candidate.pssKb > 0) {
                    plan.victims.add(candidate);
                    planned += candidate.pssKb;
                }
            }
        }
        plan.plannedKb = planned;
        if (plan.victims.isEmpty()) {
            plan.skipReason = "no eligible process";
        }
        return plan;
    }

    /** Factory ProcessClassfier.m for a recent task in the light-white window. */
    private static boolean isLightWhiteRecent(Candidate candidate, List<String> dynamicProtect) {
        if (!candidate.processName.equals(candidate.packageName)) {
            return true;
        }
        if (dynamicProtect.contains(candidate.packageName)) {
            return candidate.adj <= ProcessList.PERCEPTIBLE_LOW_APP_ADJ || candidate.hasActivities;
        }
        return candidate.adj < ProcessList.CACHED_APP_MIN_ADJ;
    }

    /** Processes that are never candidates on this build. */
    static String exclusionReason(Candidate candidate, String callerPackage, int callerUid) {
        if (candidate.killed) {
            return "already killed";
        }
        if (candidate.pid <= 0) {
            return "not running";
        }
        if (candidate.persistent) {
            return "persistent";
        }
        if (candidate.adj < 0) {
            return "system adjustment";
        }
        if (candidate.isolated) {
            return "isolated";
        }
        if (candidate.uid == callerUid || callerPackage.equals(candidate.packageName)) {
            return "camera caller";
        }
        if (candidate.hasForegroundServices) {
            return "foreground service";
        }
        if (candidate.interestingToUser) {
            return "visible to user";
        }
        if (candidate.home) {
            return "home process";
        }
        if (candidate.heavyWeight) {
            return "heavy weight";
        }
        return null;
    }

    /**
     * Factory KillTargetAction$2 ordering: processes outside recent tasks first, then older
     * recent tasks before newer ones, larger footprints first within a group.
     */
    static final class RecentOrder implements Comparator<Candidate> {
        private final List<String> mRecents;

        RecentOrder(List<String> recents) {
            mRecents = recents;
        }

        @Override
        public int compare(Candidate a, Candidate b) {
            int indexA = mRecents.indexOf(a.packageName);
            int indexB = mRecents.indexOf(b.packageName);
            if (indexA >= 0 && indexB >= 0) {
                if (indexA != indexB) {
                    return indexB - indexA;
                }
            } else if (indexA >= 0) {
                return 1;
            } else if (indexB >= 0) {
                return -1;
            }
            return Long.compare(b.pssKb, a.pssKb);
        }
    }

    /**
     * Factory {@code ReclaimOnceAction.c/f} gates and amount, then the
     * {@code ProcCompactAction} candidate list. The memcg reclaim node of the factory
     * kernel configuration is not mounted on this build; the policy writes the cgroup v2
     * root reclaim file instead and falls back to compaction.
     */
    public static ReclaimPlan planReclaimOnce(Config config, int scene, String callerPackage,
            int callerUid, Action action, Sample sample, List<Candidate> candidates,
            long nowUptime, State state) {
        ReclaimPlan plan = new ReclaimPlan();
        long lowFree = config.threshold("low_free_size", DEFAULT_LOW_FREE_KB);
        boolean cooldownPassed = nowUptime > state.reclaimOnceNotBeforeUptime;
        long cameraThermal = config.threshold("camera_event_thermal_threshold",
                DEFAULT_CAMERA_THERMAL_C);
        if (!(sample.freeKb < lowFree && cooldownPassed)) {
            if (!cooldownPassed) {
                plan.skipReason = "reclaim cooldown";
                return plan;
            }
            if (sample.thermalC >= cameraThermal) {
                plan.skipReason = "thermal";
                return plan;
            }
        }
        long amount = action.target - sample.freeKb;
        if (amount <= 0) {
            plan.skipReason = "free above target";
            return plan;
        }
        long maxCpuPsi = config.threshold("max_cpu_psi", DEFAULT_MAX_CPU_PSI);
        if (sample.cpuPsi > maxCpuPsi) {
            plan.skipReason = "cpu pressure";
            return plan;
        }
        plan.reclaimKb = amount;

        // Factory ProcCompactAction.d gates.
        long compactFree = config.threshold("compact_free_threshold", DEFAULT_COMPACT_FREE_KB);
        long compactThermal = config.threshold("compact_thermal_threshold",
                DEFAULT_COMPACT_THERMAL_C);
        if (sample.freeKb > compactFree) {
            plan.compactionSkipReason = "free above compaction threshold";
        } else if (nowUptime - state.lastCompactPassUptime < COMPACT_PASS_INTERVAL_MS) {
            plan.compactionSkipReason = "compaction interval";
        } else if (sample.thermalC >= compactThermal) {
            plan.compactionSkipReason = "thermal";
        } else if (action.cpuPsiTarget > 0 && sample.cpuPsi >= action.cpuPsiTarget) {
            plan.compactionSkipReason = "cpu pressure";
        } else {
            plan.compactionAllowed = true;
            List<String> white = config.list("white_list");
            ArrayList<Candidate> eligible = new ArrayList<>();
            for (Candidate candidate : candidates) {
                if (candidate.killed || candidate.pid <= 0 || candidate.persistent
                        || candidate.uid == callerUid
                        || callerPackage.equals(candidate.packageName)
                        || candidate.adj < ProcessList.VISIBLE_APP_ADJ
                        || white.contains(candidate.processName)) {
                    continue;
                }
                Long last = state.compactedAtUptime.get(candidate.pid);
                if (last != null && nowUptime - last < COMPACT_PROCESS_INTERVAL_MS) {
                    continue;
                }
                eligible.add(candidate);
            }
            Collections.sort(eligible, (a, b) -> a.adj != b.adj
                    ? Integer.compare(b.adj, a.adj) : Long.compare(b.pssKb, a.pssKb));
            for (Candidate candidate : eligible) {
                if (plan.compactions.size() >= MAX_COMPACTIONS_PER_PASS) {
                    break;
                }
                plan.compactions.add(candidate);
            }
        }
        return plan;
    }

    /** Small helper so the bucket loop reads clearly without an array-of-generics warning. */
    private static final class Arrays2 {
        static List<ArrayList<Candidate>> of(ArrayList<Candidate> first, ArrayList<Candidate> second) {
            ArrayList<ArrayList<Candidate>> list = new ArrayList<>(2);
            list.add(first);
            list.add(second);
            return list;
        }
    }
}
