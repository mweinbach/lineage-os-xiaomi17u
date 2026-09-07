/*
 * Copyright (C) 2026 The LineageOS Project
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

package com.android.server.cameraopt;

import android.content.Context;
import android.os.BatteryManager;
import android.os.Debug;
import android.os.Handler;
import android.os.SystemClock;
import android.util.Slog;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Samples the camera status schema from platform APIs and readable kernel nodes. */
public final class CameraStatusSampler {
    private static final String TAG = "CameraStatusSampler";
    private static final int ALL_FLAGS = 0x1ff;
    private static final int LAUNCH_FLAGS = 0xc7;
    private static final int MAX_NODE_BYTES = 4096;
    private static final int MAX_RESERVE_BYTES = 65536;
    private static final int MAX_POLICIES = 64;
    private static final int MAX_THERMAL_ZONES = 256;
    private static final int MAX_RESERVE_ENTRIES = 256;
    private static final int MAX_ARRAY_VALUES = 256;
    private static final int MAX_REPORTED_ISSUES = 32;
    private static final int TIMED_SAMPLES = 3;
    private static final long SAMPLE_INTERVAL_MS = 1000;
    private static final Pattern PSI_AVG10 = Pattern.compile(
            "(?m)^some\\s+avg10=([^\\s]+)(?:\\s|$)");
    private static final Pattern POLICY_NAME = Pattern.compile("policy(\\d+)");
    private static final String CPU_FREQUENCY_ROOT = "/sys/devices/system/cpu/cpufreq";
    private static final String THERMAL_ROOT = "/sys/class/thermal";
    private static final String BOARD_TEMPERATURE =
            "/sys/devices/virtual/thermal/thermal_message/board_sensor_temp";
    private static final String RESERVE_POOL = "/sys/kernel/reserve_pool/config";

    private final Context mContext;
    private final Handler mHandler;
    private final Object mLock = new Object();
    private final ArrayList<JSONObject> mLaunchCpuSamples = new ArrayList<>();
    private final LinkedHashMap<String, String> mIssues = new LinkedHashMap<>();
    // Objects stored here are never modified after publication under mLock.
    private JSONObject mBeforeLaunch;
    private long mLaunchUptimeMs;
    private int mTimedSampleAttempts;
    private int mLaunchCount;

    private final Runnable mTimedSample = new Runnable() {
        @Override
        public void run() {
            JSONObject sample = sampleCpuFrequencyTemperature();
            boolean again;
            synchronized (mLock) {
                if (sample.length() != 0) {
                    mLaunchCpuSamples.add(sample);
                }
                mTimedSampleAttempts++;
                again = mTimedSampleAttempts < TIMED_SAMPLES;
            }
            if (again && !mHandler.postDelayed(this, SAMPLE_INTERVAL_MS)) {
                unavailable("launch_history", "handler rejected a timed sample");
            }
        }
    };

    public CameraStatusSampler(Context context, Handler handler) {
        if (context == null || handler == null) {
            throw new IllegalArgumentException("Context and Handler are required");
        }
        Context applicationContext = context.getApplicationContext();
        mContext = applicationContext == null ? context : applicationContext;
        mHandler = handler;
    }

    /** Returns only requested, successfully collected measurements. Memory values are in kB. */
    public String sample(int flags) {
        if ((flags & ~ALL_FLAGS) != 0) {
            throw new IllegalArgumentException("Unsupported camera status flags: 0x"
                    + Integer.toHexString(flags));
        }
        JSONObject result = sampleCurrent(flags);
        if ((flags & 0x100) != 0) {
            addBeforeLaunch(result);
        }
        return result.toString();
    }

    /** Call for a real camera launch event; queries and service startup do not create history. */
    public void onCameraLaunch() {
        if (!mHandler.post(() -> {
            mHandler.removeCallbacks(mTimedSample);
            long launchUptimeMs = SystemClock.uptimeMillis();
            JSONObject baseline = sampleCurrent(LAUNCH_FLAGS);
            synchronized (mLock) {
                mBeforeLaunch = baseline;
                mLaunchCpuSamples.clear();
                mTimedSampleAttempts = 0;
                mLaunchUptimeMs = launchUptimeMs;
                mLaunchCount++;
            }
            if (!mHandler.postDelayed(mTimedSample, SAMPLE_INTERVAL_MS)) {
                unavailable("launch_history", "handler rejected the first timed sample");
            }
        })) {
            unavailable("launch_history", "handler rejected the launch event");
        }
    }

    public void dump(PrintWriter writer) {
        synchronized (mLock) {
            writer.println("CameraStatusSampler:");
            writer.println("  supportedFlags=0x" + Integer.toHexString(ALL_FLAGS));
            writer.println("  launchCount=" + mLaunchCount
                    + " baselinePresent=" + (mBeforeLaunch != null));
            if (mBeforeLaunch != null) {
                writer.println("  launchUptimeMs=" + mLaunchUptimeMs
                        + " timedSampleAttempts=" + mTimedSampleAttempts
                        + " storedCpuSamples=" + mLaunchCpuSamples.size());
            }
            writer.println("  Recent unavailable sources (not measurements):");
            for (Map.Entry<String, String> entry : mIssues.entrySet()) {
                writer.println("    " + entry.getKey() + ": " + entry.getValue());
            }
        }
    }

    private JSONObject sampleCurrent(int flags) {
        JSONObject result = new JSONObject();
        if ((flags & 0x001) != 0) {
            put(result, "attr_psi_cpu", samplePsi("/proc/pressure/cpu"));
        }
        if ((flags & 0x002) != 0) {
            put(result, "attr_psi_mem", samplePsi("/proc/pressure/memory"));
        }
        if ((flags & 0x004) != 0) {
            put(result, "attr_psi_io", samplePsi("/proc/pressure/io"));
        }
        if ((flags & 0x008) != 0) {
            put(result, "attr_temp", sampleBoardTemperature());
        }
        if ((flags & 0x010) != 0) {
            put(result, "attr_battery_level", sampleBattery());
        }
        if ((flags & 0x020) != 0) {
            JSONObject sample = sampleCpuFrequencyTemperature();
            if (sample.length() != 0) {
                put(result, "attr_cpu_freq_temp", sample);
            }
        }
        if ((flags & 0x040) != 0) {
            sampleMemory(result);
        }
        if ((flags & 0x080) != 0) {
            JSONObject reserve = sampleReservePool();
            if (reserve.length() != 0) {
                put(result, "attr_reserve_pool", reserve);
            }
        }
        return result;
    }

    private Integer samplePsi(String path) {
        String content = readNode(new File(path), MAX_NODE_BYTES);
        if (content == null) return null;
        Matcher matcher = PSI_AVG10.matcher(content);
        if (matcher.find()) {
            try {
                float value = Float.parseFloat(matcher.group(1));
                if (!Float.isNaN(value) && !Float.isInfinite(value)
                        && value >= 0 && value <= 100) {
                    return Math.round(value);
                }
            } catch (NumberFormatException ignored) {
                // A malformed field is unavailable, not a measured pressure value.
            }
        }
        unavailable(path, "missing or invalid some avg10");
        return null;
    }

    private Double sampleBoardTemperature() {
        String content = readNode(new File(BOARD_TEMPERATURE), MAX_NODE_BYTES);
        if (content == null) return null;
        try {
            double degrees = Double.parseDouble(content.trim()) / 1000.0;
            if (Double.isFinite(degrees) && Math.abs(degrees * 100.0) < Long.MAX_VALUE) {
                return Math.round(degrees * 100.0) / 100.0;
            }
        } catch (NumberFormatException ignored) {
            // Preserve the distinction between failed parsing and zero degrees.
        }
        unavailable(BOARD_TEMPERATURE, "invalid millidegree temperature");
        return null;
    }

    private Integer sampleBattery() {
        try {
            Object service = mContext.getSystemService(Context.BATTERY_SERVICE);
            if (service instanceof BatteryManager) {
                int value = ((BatteryManager) service).getIntProperty(
                        BatteryManager.BATTERY_PROPERTY_CAPACITY);
                if (value >= 0 && value <= 100) return value;
            }
            unavailable("battery_capacity", "capacity property unavailable");
        } catch (RuntimeException e) {
            unavailable("battery_capacity", e.getClass().getSimpleName());
        }
        return null;
    }

    private void sampleMemory(JSONObject result) {
        // The factory jar hardcodes 20 for AVAILABLE; v8 uses that index for ACTIVE_ANON.
        long[] memory = new long[Debug.MEMINFO_COUNT];
        Arrays.fill(memory, -1L);
        try {
            Debug.getMemInfo(memory);
            putMemory(result, "attr_mem_free", memory[Debug.MEMINFO_FREE]);
            putMemory(result, "attr_mem_cache", memory[Debug.MEMINFO_CACHED]);
            putMemory(result, "attr_mem_available", memory[Debug.MEMINFO_AVAILABLE]);
        } catch (RuntimeException | LinkageError e) {
            unavailable("memory", e.getClass().getSimpleName());
        }
    }

    private void putMemory(JSONObject result, String key, long value) {
        if (value >= 0) {
            put(result, key, value);
        } else {
            unavailable(key, "Debug did not return a valid memory value");
        }
    }

    private JSONObject sampleCpuFrequencyTemperature() {
        JSONObject result = new JSONObject();
        put(result, "freq", sampleCpuFrequency());
        put(result, "temp", sampleCpuTemperature());
        return result;
    }

    private String sampleCpuFrequency() {
        File[] policies = listDirectories(CPU_FREQUENCY_ROOT, "policy", MAX_POLICIES);
        if (policies == null) return null;
        StringBuilder result = new StringBuilder();
        for (File policy : policies) {
            Matcher name = POLICY_NAME.matcher(policy.getName());
            if (!name.matches()) continue;
            Integer current = readInteger(new File(policy, "scaling_cur_freq"));
            Integer maximum = readInteger(new File(policy, "scaling_max_freq"));
            if (current == null || maximum == null || current < 0 || maximum < 0) continue;
            try {
                int id = Integer.parseInt(name.group(1));
                // Preserve raw cpufreq values (kHz) and the factory wire format.
                result.append("Core").append(id).append(':').append(current)
                        .append(',').append(maximum).append(';');
            } catch (NumberFormatException e) {
                unavailable(policy.getPath(), "invalid policy identifier");
            }
        }
        if (result.length() == 0) {
            unavailable(CPU_FREQUENCY_ROOT, "no complete readable frequency pair");
            return null;
        }
        return result.toString();
    }

    private Integer sampleCpuTemperature() {
        File[] zones = listDirectories(THERMAL_ROOT, "thermal_zone", MAX_THERMAL_ZONES);
        if (zones == null) return null;
        Integer maximum = null;
        for (File zone : zones) {
            String type = readNode(new File(zone, "type"), MAX_NODE_BYTES);
            if (type == null) continue;
            type = type.trim();
            if (!type.startsWith("cpu") || type.startsWith("cpu-hw")) continue;
            Integer temperature = readInteger(new File(zone, "temp"));
            if (temperature != null && (maximum == null || temperature > maximum)) {
                // This field is the raw thermal value, normally millidegrees; do not divide.
                maximum = temperature;
            }
        }
        if (maximum == null) unavailable(THERMAL_ROOT, "no readable CPU temperature");
        return maximum;
    }

    private JSONObject sampleReservePool() {
        JSONObject result = new JSONObject();
        String content = readNode(new File(RESERVE_POOL), MAX_RESERVE_BYTES);
        if (content == null) return result;
        int entries = 0;
        for (String rawLine : content.split("\\n")) {
            String line = rawLine.trim();
            if (line.isEmpty()) continue;
            if (++entries > MAX_RESERVE_ENTRIES) {
                unavailable(RESERVE_POOL, "entry limit exceeded");
                break;
            }
            String key;
            String values;
            int bracket = line.indexOf('[');
            int end = line.indexOf(']');
            if (bracket > 0 && end > bracket && line.substring(end + 1).trim().isEmpty()) {
                key = line.substring(0, bracket).trim();
                values = line.substring(bracket + 1, end).trim();
            } else if (bracket == -1 && end == -1 && line.lastIndexOf(' ') > 0) {
                int split = line.lastIndexOf(' ');
                key = line.substring(0, split).trim();
                values = line.substring(split + 1).trim();
            } else {
                unavailable(RESERVE_POOL, "malformed reserve entry");
                continue;
            }
            if (key.isEmpty() || values.isEmpty()) continue;
            String[] tokens = values.split("\\s+");
            if (tokens.length > MAX_ARRAY_VALUES) {
                unavailable(RESERVE_POOL, "array limit exceeded");
                continue;
            }
            JSONArray array = new JSONArray();
            boolean valid = true;
            for (String token : tokens) {
                try {
                    array.put(Integer.parseInt(token));
                } catch (NumberFormatException e) {
                    valid = false;
                    break;
                }
            }
            if (valid) {
                put(result, key, array);
            } else {
                unavailable(RESERVE_POOL, "invalid integer in reserve entry");
            }
        }
        return result;
    }

    private void addBeforeLaunch(JSONObject result) {
        JSONObject baseline;
        List<JSONObject> samples;
        synchronized (mLock) {
            if (mBeforeLaunch == null) return;
            baseline = mBeforeLaunch;
            samples = new ArrayList<>(mLaunchCpuSamples);
        }
        copy(baseline, "attr_psi_cpu", result, "attr_psi_pre_cpu");
        copy(baseline, "attr_psi_mem", result, "attr_psi_pre_mem");
        copy(baseline, "attr_psi_io", result, "attr_psi_pre_io");
        copy(baseline, "attr_mem_free", result, "attr_mem_pre_free");
        copy(baseline, "attr_mem_cache", result, "attr_mem_pre_cache");
        copy(baseline, "attr_mem_available", result, "attr_mem_pre_available");
        JSONObject reserveBefore = baseline.optJSONObject("attr_reserve_pool");
        if (reserveBefore != null) {
            copy(reserveBefore, "source_pool_free_order", result, "attr_source_pool_free_order");
            copy(reserveBefore, "reserve_pool_free_order", result, "attr_reserve_pool_free_order");
            JSONObject reserveNow = sampleReservePool();
            putDelta(result, "attr_reserve_slowpath_count", "reserve_slowpath",
                    reserveBefore, reserveNow);
            putDelta(result, "attr_reserve_long_slowpath_count", "reserve_long_slowpath",
                    reserveBefore, reserveNow);
        }
        JSONObject fresh = sampleCpuFrequencyTemperature();
        if (fresh.length() != 0) samples.add(fresh);
        if (!samples.isEmpty()) {
            JSONArray array = new JSONArray();
            for (JSONObject sample : samples) array.put(sample);
            put(result, "attr_launch_cpu_samples", array);
        }
    }

    private void putDelta(JSONObject result, String output, String counter,
            JSONObject before, JSONObject current) {
        JSONArray previous = before.optJSONArray(counter);
        JSONArray now = current.optJSONArray(counter);
        if (previous == null || now == null || previous.length() == 0 || now.length() == 0) {
            return;
        }
        try {
            long oldValue = previous.getInt(0);
            long newValue = now.getInt(0);
            long difference = newValue - oldValue;
            if (oldValue >= 0 && newValue >= 0 && difference >= 0
                    && difference <= Integer.MAX_VALUE) {
                put(result, output, (int) difference);
            } else {
                unavailable(output, "counter reset, invalid counter, or delta overflow");
            }
        } catch (JSONException e) {
            unavailable(output, "missing integer counter");
        }
    }

    private void copy(JSONObject source, String input, JSONObject target, String output) {
        Object value = source.opt(input);
        if (value != null && value != JSONObject.NULL) put(target, output, value);
    }

    private Integer readInteger(File path) {
        String content = readNode(path, MAX_NODE_BYTES);
        if (content == null) return null;
        try {
            return Integer.parseInt(content.trim());
        } catch (NumberFormatException e) {
            unavailable(path.getPath(), "invalid integer");
            return null;
        }
    }

    private File[] listDirectories(String path, String prefix, int limit) {
        try {
            File[] files = new File(path).listFiles(
                    file -> file.getName().startsWith(prefix) && file.isDirectory());
            if (files == null || files.length == 0) {
                unavailable(path, "no readable matching directories");
                return null;
            }
            if (files.length > limit) {
                unavailable(path, "directory limit exceeded");
                return null;
            }
            Arrays.sort(files, Comparator.comparing(File::getName));
            return files;
        } catch (SecurityException e) {
            unavailable(path, "access denied");
            return null;
        }
    }

    private String readNode(File path, int limit) {
        try (FileInputStream stream = new FileInputStream(path);
                ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[Math.min(4096, limit + 1)];
            int count;
            while ((count = stream.read(buffer, 0,
                    Math.min(buffer.length, limit + 1 - output.size()))) != -1) {
                if (count == 0) {
                    unavailable(path.getPath(), "read made no progress");
                    return null;
                }
                output.write(buffer, 0, count);
                if (output.size() > limit) {
                    unavailable(path.getPath(), "byte limit exceeded");
                    return null;
                }
            }
            if (output.size() == 0) {
                unavailable(path.getPath(), "empty node");
                return null;
            }
            return new String(output.toByteArray(), StandardCharsets.UTF_8);
        } catch (IOException | SecurityException e) {
            unavailable(path.getPath(), e.getClass().getSimpleName());
            return null;
        }
    }

    private void put(JSONObject target, String key, Object value) {
        if (value == null) return;
        try {
            target.put(key, value);
        } catch (JSONException e) {
            unavailable(key, "cannot encode measured value");
        }
    }

    private void unavailable(String source, String reason) {
        boolean changed;
        synchronized (mLock) {
            String old = mIssues.get(source);
            changed = !reason.equals(old);
            if (changed) {
                mIssues.remove(source);
                mIssues.put(source, reason);
                if (mIssues.size() > MAX_REPORTED_ISSUES) {
                    mIssues.remove(mIssues.keySet().iterator().next());
                }
            }
        }
        if (changed) Slog.w(TAG, source + ": " + reason);
    }
}
