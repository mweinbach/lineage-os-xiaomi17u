/* SPDX-License-Identifier: Apache-2.0 */
package org.nezha.camerametadataprobe;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.FileOutputStream;
import java.lang.reflect.Array;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.TreeSet;

/** Inspects characteristics only: never opens a camera or creates a capture session. */
public final class ProbeActivity extends Activity {
    private TextView result;
    private Button inspect;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(24, 48, 24, 24);
        TextView description = new TextView(this);
        description.setText("Reads camera IDs and stream metadata. No camera preview, photos, "
                + "recording, networking, or device settings changes. Camera permission matches "
                + "Aperture, but this app has a different package and UID.");
        layout.addView(description);
        inspect = new Button(this);
        inspect.setText("Inspect camera metadata");
        inspect.setOnClickListener(v -> {
            if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[] {Manifest.permission.CAMERA}, 1);
            } else {
                runProbe();
            }
        });
        layout.addView(inspect);
        result = new TextView(this);
        result.setTextIsSelectable(true);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(result);
        layout.addView(scroll);
        setContentView(layout);
    }

    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(request, permissions, grants);
        if (request == 1 && grants.length == 1 && grants[0] == PackageManager.PERMISSION_GRANTED) {
            runProbe();
        } else {
            result.setText("Camera permission denied; no metadata query performed.");
        }
    }

    private void runProbe() {
        inspect.setEnabled(false);
        new Thread(() -> {
            JSONObject report = new JSONObject();
            try {
                report.put("schema_version", 1);
                report.put("package", getPackageName());
                report.put("target_sdk", getApplicationInfo().targetSdkVersion);
                report.put("camera_permission", true);
                report.put("system_camera_permission", checkSelfPermission("android.permission.SYSTEM_CAMERA")
                        == PackageManager.PERMISSION_GRANTED);
                CameraManager manager = getSystemService(CameraManager.class);
                String[] ids = manager.getCameraIdList();
                report.put("visible_ids", new JSONArray(ids));
                JSONArray cameras = new JSONArray();
                report.put("cameras", cameras);
                Set<String> physicalIds = new TreeSet<>();
                for (String id : ids) {
                    cameras.put(inspectCamera(manager, id, false, physicalIds));
                }
                for (String id : physicalIds) {
                    cameras.put(inspectCamera(manager, id, true, new TreeSet<>()));
                }
            } catch (Exception error) {
                try { report.put("probe_error", error.toString()); } catch (Exception ignored) { }
            }
            String text = report.toString();
            try (FileOutputStream stream = openFileOutput("camera-metadata.json", MODE_PRIVATE)) {
                stream.write(text.getBytes(StandardCharsets.UTF_8));
            } catch (Exception error) {
                Log.e("NezhaCameraProbe", "Unable to save report: " + error);
            }
            // Each line contains only IDs, metadata counts and exceptions; no images or accounts.
            Log.i("NezhaCameraProbe", "Report saved to private camera-metadata.json");
            runOnUiThread(() -> { result.setText(text); inspect.setEnabled(true); });
        }, "CameraMetadataProbe").start();
    }

    private static JSONObject inspectCamera(CameraManager manager, String id, boolean physical,
            Set<String> physicalIds) throws Exception {
        JSONObject row = new JSONObject();
        row.put("id", id);
        row.put("physical", physical);
        try {
            CameraCharacteristics characteristics = manager.getCameraCharacteristics(id);
            row.put("lens_facing", characteristics.get(CameraCharacteristics.LENS_FACING));
            row.put("capabilities", new JSONArray(characteristics.get(
                    CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)));
            physicalIds.addAll(characteristics.getPhysicalCameraIds());
            row.put("physical_ids", new JSONArray(characteristics.getPhysicalCameraIds()));
            JSONObject entries = new JSONObject();
            row.put("stream_keys", entries);
            for (CameraCharacteristics.Key<?> key : characteristics.getKeys()) {
                String name = key.getName();
                if (name.startsWith("android.") && (name.contains("StreamConfigurations")
                        || name.contains("MinFrameDurations") || name.contains("StallDurations"))) {
                    try {
                        Object value = characteristics.get(key);
                        entries.put(name, value == null ? "null" : value.getClass().isArray()
                                ? Array.getLength(value) : value.getClass().getSimpleName());
                    } catch (Exception error) {
                        entries.put(name, error.toString());
                    }
                }
            }
            try {
                StreamConfigurationMap map = characteristics.get(
                        CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                row.put("standard_map", map == null ? "null" : "ok");
                if (map != null) row.put("output_formats", new JSONArray(map.getOutputFormats()));
            } catch (Exception error) {
                row.put("standard_map_error", error.toString());
            }
            try {
                StreamConfigurationMap map = characteristics.get(
                        CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP_MAXIMUM_RESOLUTION);
                row.put("maximum_resolution_map", map == null ? "null" : "ok");
            } catch (Exception error) {
                row.put("maximum_resolution_map_error", error.toString());
            }
        } catch (Exception error) {
            row.put("characteristics_error", error.toString());
        }
        Log.i("NezhaCameraProbe", row.toString());
        return row;
    }
}
