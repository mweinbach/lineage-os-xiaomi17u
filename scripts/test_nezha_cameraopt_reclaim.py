#!/usr/bin/env python3
"""Exercise the CameraOpt reclaim planner on a host JVM with synthetic tables and processes.

The planner is pure Java over org.json and one ProcessList constant class. This
harness compiles it against a minimal org.json and a constants stub, then runs
PlannerHarness, whose assertions replay the factory semantics recovered from the
retained bytecode: range conditions, the 60 s capture spacing, the memory gap,
bucket order, the authored adjustment floor, per-process thresholds for white
processes, and the reclaim-once and compaction gates. Nothing here touches a
phone or a build tree.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / ("device/xiaomi/nezha/cameraopt-service/process-policy/src/com/android/server/am/"
                  "NezhaCameraReclaimPlanner.java")

PROCESS_LIST = """package com.android.server.am;
public final class ProcessList {
    public static final int CACHED_APP_MAX_ADJ = 999;
    public static final int CACHED_APP_MIN_ADJ = 900;
    public static final int SERVICE_B_ADJ = 800;
    public static final int PERCEPTIBLE_LOW_APP_ADJ = 250;
    public static final int PERCEPTIBLE_APP_ADJ = 200;
    public static final int VISIBLE_APP_ADJ = 100;
}
"""

JSON_OBJECT = r'''package org.json;
import java.util.*;
public class JSONObject {
    final LinkedHashMap<String, Object> map = new LinkedHashMap<>();
    public static final Object NULL = new Object();
    public JSONObject() {}
    public JSONObject(String text) throws JSONException {
        Object value = new Parser(text).parseTop();
        if (!(value instanceof JSONObject)) throw new JSONException("not an object");
        map.putAll(((JSONObject) value).map);
    }
    public JSONObject put(String key, Object value) { map.put(key, value); return this; }
    public boolean has(String key) { return map.containsKey(key); }
    public Object opt(String key) { return map.get(key); }
    public Iterator<String> keys() { return new ArrayList<>(map.keySet()).iterator(); }
    public int length() { return map.size(); }
    public JSONObject optJSONObject(String key) { Object v = map.get(key); return v instanceof JSONObject ? (JSONObject) v : null; }
    public JSONArray optJSONArray(String key) { Object v = map.get(key); return v instanceof JSONArray ? (JSONArray) v : null; }
    public String optString(String key, String fallback) { Object v = map.get(key); return v == null || v == NULL ? fallback : String.valueOf(v); }
    public String optString(String key) { return optString(key, ""); }
    public boolean optBoolean(String key, boolean fallback) { Object v = map.get(key); if (v instanceof Boolean) return (Boolean) v; if (v instanceof String) { if ("true".equalsIgnoreCase((String) v)) return true; if ("false".equalsIgnoreCase((String) v)) return false; } return fallback; }
    public long optLong(String key, long fallback) { Object v = map.get(key); if (v instanceof Number) return ((Number) v).longValue(); if (v instanceof String) { try { return (long) Double.parseDouble((String) v); } catch (NumberFormatException e) { return fallback; } } return fallback; }
    public int optInt(String key, int fallback) { return (int) optLong(key, fallback); }
    public double optDouble(String key, double fallback) { Object v = map.get(key); if (v instanceof Number) return ((Number) v).doubleValue(); return fallback; }
    @Override public String toString() { StringBuilder b = new StringBuilder("{"); boolean first = true; for (Map.Entry<String, Object> e : map.entrySet()) { if (!first) b.append(','); first = false; b.append('"').append(e.getKey()).append("\":").append(render(e.getValue())); } return b.append('}').toString(); }
    static String render(Object v) { if (v instanceof String) return '"' + ((String) v).replace("\\", "\\\\").replace("\"", "\\\"") + '"'; return String.valueOf(v); }
    static final class Parser {
        final String s; int i;
        Parser(String s) { this.s = s; }
        Object parseTop() throws JSONException { Object v = value(); ws(); if (i != s.length()) throw new JSONException("trailing"); return v; }
        void ws() { while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++; }
        Object value() throws JSONException {
            ws(); if (i >= s.length()) throw new JSONException("eof");
            char c = s.charAt(i);
            if (c == '{') { i++; JSONObject o = new JSONObject(); ws(); if (peek('}')) { i++; return o; } while (true) { ws(); String k = string(); ws(); expect(':'); Object v = value(); o.map.put(k, v); ws(); if (peek(',')) { i++; continue; } expect('}'); return o; } }
            if (c == '[') { i++; JSONArray a = new JSONArray(); ws(); if (peek(']')) { i++; return a; } while (true) { a.list.add(value()); ws(); if (peek(',')) { i++; continue; } expect(']'); return a; } }
            if (c == '"') return string();
            if (s.startsWith("true", i)) { i += 4; return Boolean.TRUE; }
            if (s.startsWith("false", i)) { i += 5; return Boolean.FALSE; }
            if (s.startsWith("null", i)) { i += 4; return NULL; }
            int start = i; while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) i++;
            String num = s.substring(start, i); if (num.isEmpty()) throw new JSONException("bad token at " + i);
            if (num.contains(".") || num.contains("e") || num.contains("E")) return Double.parseDouble(num);
            return Long.parseLong(num);
        }
        boolean peek(char c) { return i < s.length() && s.charAt(i) == c; }
        void expect(char c) throws JSONException { ws(); if (!peek(c)) throw new JSONException("expected " + c + " at " + i); i++; }
        String string() throws JSONException { expect('"'); StringBuilder b = new StringBuilder(); while (i < s.length()) { char c = s.charAt(i++); if (c == '"') return b.toString(); if (c == '\\') { char n = s.charAt(i++); if (n == 'u') { b.append((char) Integer.parseInt(s.substring(i, i + 4), 16)); i += 4; } else if (n == 'n') b.append('\n'); else if (n == 't') b.append('\t'); else b.append(n); } else b.append(c); } throw new JSONException("unterminated string"); }
    }
}
'''

JSON_ARRAY = '''package org.json;
import java.util.*;
public class JSONArray {
    final ArrayList<Object> list = new ArrayList<>();
    public JSONArray() {}
    public int length() { return list.size(); }
    public Object opt(int index) { return index >= 0 && index < list.size() ? list.get(index) : null; }
    public JSONObject optJSONObject(int index) { Object v = opt(index); return v instanceof JSONObject ? (JSONObject) v : null; }
    public String optString(int index, String fallback) { Object v = opt(index); return v == null || v == JSONObject.NULL ? fallback : String.valueOf(v); }
    public JSONArray put(Object value) { list.add(value); return this; }
    @Override public String toString() { StringBuilder b = new StringBuilder("["); for (int i = 0; i < list.size(); i++) { if (i > 0) b.append(','); b.append(JSONObject.render(list.get(i))); } return b.append(']').toString(); }
}
'''

JSON_EXCEPTION = ("package org.json;\npublic class JSONException extends Exception {\n"
                  "    private static final long serialVersionUID = 1L;\n"
                  "    public JSONException(String m) { super(m); }\n}\n")

# Synthetic table in the factory shape. Numbers differ from the device tables on purpose.
TABLE = {
    "support": {"trim_memory_support": True, "deep_kill_support": False},
    "threshold": {
        "adj_threshold": 800, "lowerAdj_freeMem_threshold": 600000, "lowAdj_threshold": 0,
        "3rd_lowAdj_threshold": 50, "kill_tag": 63, "3rd_kill_tag": 63,
        "kill_highprio_sysapp_threshlod": 30000, "kill_lowprio_sysapp_threshlod": 10000,
        "skip_task": 2, "skip_task_lower": 1, "restart_kill_duration": 2000,
        "duration_reclaim_capture": 60000, "camera_event_thermal_threshold": 54,
        "low_free_size": 150000, "compact_free_threshold": 150000, "max_cpu_psi": 99,
    },
    "configs": [
        {"name": "white_list", "config": ["com.example.white", "com.example.whitebig"]},
        {"name": "light_white_list", "config": ["com.example.light"]},
        {"name": "perceptible_list", "config": ["com.example.perceptible"]},
        {"name": "protect_list", "config": ["com.example.protect"]},
        {"name": "dynamic_protect_list", "config": []},
    ],
    "kill_configs": [
        {"name": "pss_threshold", "config": {"com.example.whitebig": 100000}},
        {"name": "adj_threshold", "config": {"com.example.whitebig": 250}},
    ],
    "ReclaimActions": {
        "kill_target": {
            "miuicam_capture_event": [{"enable": True, "free_target": 400000, "kill_level": 0,
                                       "target": 1200000, "trigger": {"availablemem": "0:-1"}}],
            "200M_scene_event": [{"cpu_psi_target": 55, "enable": True, "free_target": "700000",
                                  "target": "2800000",
                                  "trigger": {"cache": "1000000:-1", "free": "0:700000"}}],
            "video_4k_dolby_event": [{"enable": False, "free_target": 600000, "target": 1800000,
                                      "trigger": {"availablemem": "0:-1"}}],
        },
        "reclaim_once": {
            "miuicam_capture_event": [{"cpu_psi_target": 99, "enable": True, "target": 300000,
                                       "trigger": {"availablemem": "1500000:-1", "free": "0:300000"}}],
        },
        "kill_once": {
            "psi_monitor": [{"cpu_psi_target": 50, "enable": True, "kill_level": 0,
                             "trigger": {"free": "0:100000", "some_mem_psi": "4:-1"}}],
        },
    },
}

HARNESS = r'''package com.android.server.am;
import com.android.server.am.NezhaCameraReclaimPlanner.*;
import org.json.JSONObject;
import java.util.*;
public final class PlannerHarness {
    static int checks;
    static void check(boolean ok, String what) { checks++; if (!ok) throw new AssertionError(what); }
    static Candidate proc(int pid, int uid, String pkg, String name, int adj, long pss) {
        Candidate c = new Candidate(); c.pid = pid; c.uid = uid; c.packageName = pkg; c.processName = name;
        c.adj = adj; c.pssKb = pss; return c;
    }
    static Sample sample(long free, long avail, long cached, long total) {
        Sample s = new Sample(); s.freeKb = free; s.availableKb = avail; s.cachedKb = cached; s.totalKb = total;
        s.fileMemKb = cached; s.thermalC = 30f; return s;
    }
    public static void main(String[] args) throws Exception {
        Config config = Config.parse(new JSONObject(args[0]));
        check(config.actionCount() == 5, "five actions parsed: " + config.actionCount());
        check(config.droppedEntries() == 0, "nothing dropped");
        check(config.support("trim_memory_support") && !config.support("deep_kill_support"), "support flags");
        check(config.threshold("adj_threshold", -1) == 800 && config.threshold("absent", 7) == 7, "threshold lookup");
        check(config.list("white_list").size() == 2 && config.list("absent").isEmpty(), "lists");
        check(config.killPssThreshold("com.example.whitebig") == 100000 && config.killPssThreshold("x") == 0, "kill configs");
        // Conditions: strict range, -1 is unbounded, numeric strings accepted.
        Action capture = config.actions("kill_target", "miuicam_capture_event").get(0);
        check(capture.freeTarget == 400000 && capture.target == 1200000, "capture numbers");
        Action twoHundred = config.actions("kill_target", "200M_scene_event").get(0);
        check(twoHundred.freeTarget == 700000 && twoHundred.target == 2800000 && twoHundred.cpuPsiTarget == 55, "string numbers");
        check(twoHundred.triggers.size() == 2, "two triggers");
        check(capture.matches(sample(1, 1, 0, 8000000)), "availablemem 0:-1 matches any positive value");
        check(!capture.matches(sample(1, 0, 0, 8000000)), "availablemem strict lower bound");
        check(twoHundred.matches(sample(699999, 5000000, 1000001, 8000000)), "200M trigger inside ranges");
        check(!twoHundred.matches(sample(700000, 5000000, 1000001, 8000000)), "200M free upper bound is strict");
        check(!twoHundred.matches(sample(1000, 5000000, 1000000, 8000000)), "200M cache lower bound is strict");
        check(!config.actions("kill_target", "video_4k_dolby_event").get(0).matches(sample(1, 1, 1, 1)), "disabled never matches");
        Action psi = config.actions("kill_once", "psi_monitor").get(0);
        check(!psi.matches(sample(1000, 1, 1, 1)), "psi condition never matches an unsampled (-1) psi");
        // Scene mapping.
        check(NezhaCameraReclaimPlanner.sceneForModeLevel(0x101) == NezhaCameraReclaimPlanner.SCENE_VIDEO_SWITCH, "4K");
        check(NezhaCameraReclaimPlanner.sceneForModeLevel(0x102) == NezhaCameraReclaimPlanner.SCENE_VIDEO_SWITCH, "8K");
        check(NezhaCameraReclaimPlanner.sceneForModeLevel(0x103) == NezhaCameraReclaimPlanner.SCENE_VIDEO_4K_DOLBY, "dolby");
        check(NezhaCameraReclaimPlanner.sceneForModeLevel(0x201) == NezhaCameraReclaimPlanner.SCENE_200M, "200M");
        check(NezhaCameraReclaimPlanner.sceneForModeLevel(0x202) == NezhaCameraReclaimPlanner.SCENE_LIVE_MOTION, "live");
        check(NezhaCameraReclaimPlanner.sceneForModeLevel(0x999) == NezhaCameraReclaimPlanner.SCENE_VIDEO_SWITCH, "unknown level falls to video switch");
        check(!NezhaCameraReclaimPlanner.isKnownModeLevel(0x999) && NezhaCameraReclaimPlanner.isKnownModeLevel(0x201), "known levels");
        check("miuicam_capture_event".equals(NezhaCameraReclaimPlanner.sceneName(9)) && NezhaCameraReclaimPlanner.sceneName(99) == null, "scene names");
        // Capture spacing.
        // Like the factory, the interval is measured from uptime zero, so the first
        // minute after boot is also spaced.
        State state = new State();
        check(!NezhaCameraReclaimPlanner.captureReclaimAllowed(config, state, 100), "capture in the first minute of uptime refused");
        check(NezhaCameraReclaimPlanner.captureReclaimAllowed(config, state, 10_000_000), "first capture allowed");
        state.lastCaptureReclaimUptime = 10_000_000;
        check(!NezhaCameraReclaimPlanner.captureReclaimAllowed(config, state, 10_059_999), "second capture inside 60 s refused");
        check(NezhaCameraReclaimPlanner.captureReclaimAllowed(config, state, 10_060_100), "capture after 60 s allowed");
        // Kill plan: gap, floor, exclusions, ordering.
        String camera = NezhaCameraReclaimPlanner.CAMERA_PACKAGE;
        List<Candidate> procs = new ArrayList<>();
        procs.add(proc(1, 10001, camera, camera, 0, 900000));
        Candidate fgs = proc(2, 10002, "com.example.fgs", "com.example.fgs", 950, 300000); fgs.hasForegroundServices = true; procs.add(fgs);
        Candidate visible = proc(3, 10003, "com.example.vis", "com.example.vis", 950, 300000); visible.interestingToUser = true; procs.add(visible);
        Candidate persistent = proc(4, 1000, "android", "system", -900, 300000); persistent.persistent = true; procs.add(persistent);
        Candidate home = proc(5, 10005, "com.example.home", "com.example.home", 600, 300000); home.home = true; procs.add(home);
        Candidate prev = proc(6, 10006, "com.example.prev", "com.example.prev", 700, 300000); procs.add(prev);
        Candidate big3 = proc(7, 10007, "com.example.big", "com.example.big", 950, 250000); procs.add(big3);
        Candidate small3 = proc(8, 10008, "com.example.small", "com.example.small", 950, 50000); procs.add(small3);
        Candidate recent3 = proc(9, 10009, "com.example.recent", "com.example.recent", 950, 260000); procs.add(recent3);
        Candidate sys = proc(10, 10010, "com.example.sys", "com.example.sys", 950, 40000); sys.systemApp = true; procs.add(sys);
        Candidate sysTiny = proc(11, 10011, "com.example.systiny", "com.example.systiny", 950, 20000); sysTiny.systemApp = true; procs.add(sysTiny);
        Candidate white = proc(12, 10012, "com.example.white", "com.example.white", 950, 500000); procs.add(white);
        Candidate whiteBig = proc(13, 10013, "com.example.whitebig", "com.example.whitebig", 950, 150000); procs.add(whiteBig);
        Candidate protect = proc(14, 10014, "com.example.protect", "com.example.protect", 950, 120000); procs.add(protect);
        Candidate light = proc(15, 10015, "com.example.light", "com.example.light", 950, 70000); procs.add(light);
        Candidate iso = proc(16, 99001, "com.example.iso", "com.example.iso:isolated", 950, 80000); iso.isolated = true; procs.add(iso);
        List<String> recents = Arrays.asList("com.example.recent", "com.example.older");
        // Plenty of memory: no gap, nothing killed.
        Sample rich = sample(1000000, 6000000, 3000000, 8000000);
        KillPlan none = NezhaCameraReclaimPlanner.planKill(config, 9, camera, 10001, capture, rich, procs, recents, 100000, state);
        check(none.victims.isEmpty() && "no memory gap".equals(none.skipReason), "no gap: " + none);
        // Free below free_target by 300 MB: gap 300000 kB, MemFree under 600 MB escalates the factory threshold to 0.
        Sample tight = sample(100000, 6000000, 3000000, 8000000);
        KillPlan plan = NezhaCameraReclaimPlanner.planKill(config, 9, camera, 10001, capture, tight, procs, recents, 100000, state);
        check(plan.gapKb == 300000, "gap = free_target - free: " + plan.gapKb);
        check(plan.factoryAdjThreshold == 0 && plan.effectiveAdjThreshold == 800 && plan.escalationSuppressed, "floor holds: " + plan);
        List<String> names = new ArrayList<>(); for (Candidate c : plan.victims) names.add(c.processName);
        check(!names.contains(camera) && !names.contains("com.example.fgs") && !names.contains("com.example.vis")
              && !names.contains("system") && !names.contains("com.example.home") && !names.contains("com.example.iso"), "exclusions: " + names);
        check(!names.contains("com.example.prev"), "adj 700 stays below the floor: " + names);
        check(names.get(0).equals("com.example.big") && names.get(1).equals("com.example.small"), "non-recent third-party largest first: " + names);
        check(!names.contains("com.example.systiny"), "system app under the PSS minimum is skipped: " + names);
        check(!names.contains("com.example.white"), "white process without its own threshold is never killed: " + names);
        check(plan.plannedKb >= plan.gapKb, "planned covers gap: " + plan);
        check(plan.victims.size() <= NezhaCameraReclaimPlanner.MAX_KILLS_PER_BATCH, "batch bound");
        // Only white-listed heavy processes: killed only above their own pss/adj thresholds.
        List<Candidate> whites = new ArrayList<>();
        whites.add(proc(21, 10021, "com.example.white", "com.example.white", 950, 900000));
        whites.add(proc(22, 10022, "com.example.whitebig", "com.example.whitebig", 950, 150000));
        KillPlan whitePlan = NezhaCameraReclaimPlanner.planKill(config, 9, camera, 10001, capture, tight, whites, recents, 100000, state);
        check(whitePlan.victims.size() == 1 && whitePlan.victims.get(0).processName.equals("com.example.whitebig"), "white threshold: " + whitePlan);
        // Recent ordering: non-recent first, then older recent before newer.
        List<Candidate> recentOnly = new ArrayList<>();
        recentOnly.add(proc(31, 10031, "com.example.recent", "com.example.recent", 950, 50000));
        recentOnly.add(proc(32, 10032, "com.example.older", "com.example.older", 950, 40000));
        recentOnly.add(proc(33, 10033, "com.example.fresh", "com.example.fresh", 950, 30000));
        KillPlan order = NezhaCameraReclaimPlanner.planKill(config, 9, camera, 10001, capture, tight, recentOnly, recents, 100000, state);
        check(order.victims.get(0).processName.equals("com.example.fresh") && order.victims.get(1).processName.equals("com.example.older")
              && order.victims.get(2).processName.equals("com.example.recent"), "recent order: " + order.victims);
        // Rate limits between batches and after camera foreground.
        State spaced = new State(); spaced.lastKillBatchUptime = 99000;
        check("kill batch interval".equals(NezhaCameraReclaimPlanner.planKill(config, 9, camera, 10001, capture, tight, procs, recents, 100000, spaced).skipReason), "batch spacing");
        State restarted = new State(); restarted.cameraForegroundUptime = 99000;
        check("camera restart interval".equals(NezhaCameraReclaimPlanner.planKill(config, 9, camera, 10001, capture, tight, procs, recents, 100000, restarted).skipReason), "restart spacing");
        // A third-party caller uses its own kill tag and threshold keys.
        KillPlan third = NezhaCameraReclaimPlanner.planKill(config, 9, "com.example.thirdcam", 10099, capture, tight, procs, recents, 100000, new State());
        check(third.factoryAdjThreshold == 50 && third.effectiveAdjThreshold == 800, "third-party low threshold also floored: " + third);
        // Quarter-of-RAM rule dominates when available memory is very low.
        Sample starved = sample(500000, 1000000, 300000, 8000000);
        KillPlan quarter = NezhaCameraReclaimPlanner.planKill(config, 9, camera, 10001, capture, starved, procs, recents, 100000, new State());
        check(quarter.gapKb == 1000000, "gap from quarter rule: " + quarter.gapKb);
        // Reclaim once.
        Action reclaim = config.actions("reclaim_once", "miuicam_capture_event").get(0);
        Sample lowFree = sample(100000, 2000000, 1500000, 8000000);
        check(reclaim.matches(lowFree), "reclaim trigger");
        ReclaimPlan r1 = NezhaCameraReclaimPlanner.planReclaimOnce(config, 9, camera, 10001, reclaim, lowFree, procs, 100000, new State());
        check(r1.skipReason == null && r1.reclaimKb == 200000, "reclaim amount = target - free: " + r1);
        check(r1.compactionAllowed && !r1.compactions.isEmpty(), "compaction allowed under threshold: " + r1);
        for (Candidate c : r1.compactions) check(!c.processName.equals(camera) && !c.processName.equals("com.example.white") && c.adj >= 100 && !c.persistent, "compaction exclusions: " + c);
        check(r1.compactions.get(0).adj >= r1.compactions.get(r1.compactions.size() - 1).adj, "compaction adj order");
        State cooling = new State(); cooling.reclaimOnceNotBeforeUptime = 100500;
        check("reclaim cooldown".equals(NezhaCameraReclaimPlanner.planReclaimOnce(config, 9, camera, 10001, reclaim, sample(200000, 2000000, 1500000, 8000000), procs, 100000, cooling).skipReason), "reclaim cooldown");
        Sample hot = sample(200000, 2000000, 1500000, 8000000); hot.thermalC = 60f;
        check("thermal".equals(NezhaCameraReclaimPlanner.planReclaimOnce(config, 9, camera, 10001, reclaim, hot, procs, 100000, new State()).skipReason), "thermal gate");
        check("free above target".equals(NezhaCameraReclaimPlanner.planReclaimOnce(config, 9, camera, 10001, reclaim, sample(400000, 2000000, 1500000, 8000000), procs, 100000, new State()).skipReason), "target gate");
        Sample busy = sample(100000, 2000000, 1500000, 8000000); busy.cpuPsi = 99.5f;
        check("cpu pressure".equals(NezhaCameraReclaimPlanner.planReclaimOnce(config, 9, camera, 10001, reclaim, busy, procs, 100000, new State()).skipReason), "cpu gate");
        State compactedRecently = new State(); compactedRecently.compactedAtUptime.put(7, 99000L);
        ReclaimPlan r2 = NezhaCameraReclaimPlanner.planReclaimOnce(config, 9, camera, 10001, reclaim, lowFree, procs, 100000, compactedRecently);
        for (Candidate c : r2.compactions) check(c.pid != 7, "per-process compaction cooldown");
        ReclaimPlan r3 = NezhaCameraReclaimPlanner.planReclaimOnce(config, 9, camera, 10001, reclaim, sample(200000, 2000000, 1500000, 8000000), procs, 100000, new State());
        check(r3.skipReason == null && !r3.compactionAllowed && "free above compaction threshold".equals(r3.compactionSkipReason), "compaction threshold: " + r3);
        // Empty or malformed tables never throw.
        Config empty = Config.parse(null);
        check(empty.actionCount() == 0 && empty.actions("kill_target", "miuicam_capture_event").isEmpty(), "empty config");
        Config odd = Config.parse(new JSONObject("{\"ReclaimActions\":{\"kill_target\":{\"miuicam_capture_event\":[{\"enable\":true,\"trigger\":{\"free\":\"nonsense\",\"cache\":\"1:2:3\"}}]}},\"configs\":[{\"name\":\"white_list\"}]}"));
        check(odd.actionCount() == 1 && odd.droppedEntries() == 3, "malformed entries dropped: " + odd.droppedEntries());
        System.out.println("{\"checks\": " + checks + ", \"victims\": " + names.size() + ", \"gap_kb\": " + plan.gapKb + "}");
    }
}
'''


def find_javac() -> str | None:
    candidates = [shutil.which("javac")]
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(str(Path(java_home) / "bin/javac"))
    candidates += sorted(glob.glob("/Applications/Android Studio*.app/Contents/jbr/Contents/Home/bin/javac"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def run(javac: str | None = None) -> dict:
    javac = javac or find_javac()
    if javac is None:
        raise RuntimeError("javac is unavailable")
    java = str(Path(javac).with_name("java"))
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src = root / "src"
        files = {
            "com/android/server/am/NezhaCameraReclaimPlanner.java": PLANNER.read_text(),
            "com/android/server/am/ProcessList.java": PROCESS_LIST,
            "com/android/server/am/PlannerHarness.java": HARNESS,
            "org/json/JSONObject.java": JSON_OBJECT,
            "org/json/JSONArray.java": JSON_ARRAY,
            "org/json/JSONException.java": JSON_EXCEPTION,
        }
        for name, text in files.items():
            path = src / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        classes = root / "classes"
        classes.mkdir()
        compile_result = subprocess.run(
            [javac, "--release", "17", "-Xlint:all", "-Werror", "-d", str(classes),
             *[str(p) for p in sorted(src.rglob("*.java"))]],
            capture_output=True, text=True)
        if compile_result.returncode != 0:
            raise RuntimeError("planner compilation failed:\n" + compile_result.stderr)
        run_result = subprocess.run(
            [java, "-cp", str(classes), "com.android.server.am.PlannerHarness", json.dumps(TABLE)],
            capture_output=True, text=True)
        if run_result.returncode != 0:
            raise RuntimeError("planner harness failed:\n" + run_result.stderr + run_result.stdout)
        return json.loads(run_result.stdout.strip().splitlines()[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--javac")
    args = parser.parse_args()
    result = run(args.javac)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
