/* SPDX-License-Identifier: Apache-2.0 */
package org.nezha.cameracaptureprobe;

import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraExtensionCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.util.Size;
import org.json.JSONArray;
import org.json.JSONObject;
import java.lang.reflect.Array;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/** Characteristics and platform-extension queries only. Never opens a camera. */
final class CameraInventory {
    static JSONObject inspect(CameraManager manager) throws Exception {
        JSONObject out = new JSONObject();
        String[] ids = manager.getCameraIdList();
        out.put("visible_ids", new JSONArray(ids));
        JSONArray cameras = new JSONArray();
        Set<String> physical = new TreeSet<>();
        Set<String> visible = new HashSet<>();
        for (String id : ids) {
            visible.add(id);
            cameras.put(camera(manager, id, false, physical));
        }
        for (String id : physical) {
            if (!visible.contains(id)) cameras.put(camera(manager, id, true, new TreeSet<>()));
        }
        out.put("cameras", cameras);
        out.put("extension_query_scope", "Platform Camera2 extensions; query may initialize proxy, "
                + "but does not create a session or capture media. Numeric IDs are Camera2 values.");
        return out;
    }

    private static JSONObject camera(CameraManager manager, String id, boolean physicalOnly,
            Set<String> physical) throws Exception {
        JSONObject out = new JSONObject();
        out.put("id", id);
        out.put("physical_only", physicalOnly);
        try {
            CameraCharacteristics c = manager.getCameraCharacteristics(id);
            out.put("lens_facing", c.get(CameraCharacteristics.LENS_FACING));
            out.put("sensor_orientation", c.get(CameraCharacteristics.SENSOR_ORIENTATION));
            out.put("capabilities", array(c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)));
            out.put("focal_lengths", array(c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)));
            out.put("physical_ids", new JSONArray(c.getPhysicalCameraIds()));
            physical.addAll(c.getPhysicalCameraIds());
            out.put("pixel_array", string(c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE)));
            out.put("active_array", string(c.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)));
            out.put("maximum_pixel_array", string(c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE_MAXIMUM_RESOLUTION)));
            out.put("maximum_active_array", string(c.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE_MAXIMUM_RESOLUTION)));
            out.put("available_stream_use_cases", array(c.get(CameraCharacteristics.SCALER_AVAILABLE_STREAM_USE_CASES)));
            JSONArray requests = new JSONArray();
            List<CaptureRequest.Key<?>> requestKeys = c.getAvailableCaptureRequestKeys();
            if (requestKeys != null) for (CaptureRequest.Key<?> key : requestKeys) requests.put(key.getName());
            out.put("available_request_keys", requests);
            for (boolean maximum : new boolean[]{false, true}) {
                String name = maximum ? "maximum_resolution_map" : "standard_map";
                try {
                    StreamConfigurationMap map = c.get(maximum
                            ? CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP_MAXIMUM_RESOLUTION
                            : CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                    out.put(name, map == null ? JSONObject.NULL : streamMap(map));
                } catch (Exception error) { out.put(name + "_error", error.toString()); }
            }
            // Each extension format is isolated: one unsupported format must not erase the rest.
            if (!physicalOnly) {
                try { out.put("extensions", extensions(manager.getCameraExtensionCharacteristics(id))); }
                catch (Exception error) { out.put("extensions_error", error.toString()); }
            }
        } catch (Exception error) { out.put("characteristics_error", error.toString()); }
        return out;
    }

    private static JSONObject streamMap(StreamConfigurationMap map) throws Exception {
        JSONObject out = new JSONObject();
        out.put("output_formats", array(map.getOutputFormats()));
        JSONArray formats = new JSONArray();
        for (int format : map.getOutputFormats()) {
            JSONObject row = new JSONObject();
            row.put("format", format);
            row.put("name", formatName(format));
            try { row.put("normal", sizeDetails(map, format, map.getOutputSizes(format))); }
            catch (Exception error) { row.put("normal_error", error.toString()); }
            try { row.put("high_resolution", sizeDetails(map, format, map.getHighResolutionOutputSizes(format))); }
            catch (Exception error) { row.put("high_resolution_error", error.toString()); }
            formats.put(row);
        }
        out.put("formats", formats);
        try { out.put("preview_sizes", sizes(map.getOutputSizes(SurfaceTexture.class))); }
        catch (Exception error) { out.put("preview_sizes_error", error.toString()); }
        return out;
    }

    private static JSONArray sizeDetails(StreamConfigurationMap map, int format, Size[] sizes)
            throws Exception {
        JSONArray out = new JSONArray();
        if (sizes != null) for (Size size : sizes) {
            JSONObject row = new JSONObject();
            row.put("width", size.getWidth());
            row.put("height", size.getHeight());
            try {
                row.put("min_frame_duration_ns", map.getOutputMinFrameDuration(format, size));
                row.put("stall_duration_ns", map.getOutputStallDuration(format, size));
            } catch (Exception error) { row.put("duration_error", error.toString()); }
            out.put(row);
        }
        return out;
    }

    private static JSONArray extensions(CameraExtensionCharacteristics c) throws Exception {
        JSONArray out = new JSONArray();
        for (int mode : c.getSupportedExtensions()) {
            JSONObject row = new JSONObject();
            row.put("mode", mode);
            row.put("name", extensionName(mode));
            JSONObject formats = new JSONObject();
            for (int format : new int[]{ImageFormat.JPEG, ImageFormat.JPEG_R, ImageFormat.YUV_420_888}) {
                try { formats.put(formatName(format), sizes(c.getExtensionSupportedSizes(mode, format))); }
                catch (Exception error) { formats.put(formatName(format) + "_error", error.toString()); }
            }
            row.put("capture_sizes", formats);
            try { row.put("preview_sizes", sizes(c.getExtensionSupportedSizes(mode, SurfaceTexture.class))); }
            catch (Exception error) { row.put("preview_sizes_error", error.toString()); }
            out.put(row);
        }
        return out;
    }

    static String extensionName(int mode) {
        switch (mode) {
            case CameraExtensionCharacteristics.EXTENSION_AUTOMATIC: return "AUTO";
            case CameraExtensionCharacteristics.EXTENSION_FACE_RETOUCH: return "FACE_RETOUCH";
            case CameraExtensionCharacteristics.EXTENSION_BOKEH: return "BOKEH";
            case CameraExtensionCharacteristics.EXTENSION_HDR: return "HDR";
            case CameraExtensionCharacteristics.EXTENSION_NIGHT: return "NIGHT";
            default: return "UNKNOWN_" + mode;
        }
    }

    static String formatName(int format) {
        switch (format) {
            case ImageFormat.JPEG: return "JPEG";
            case ImageFormat.JPEG_R: return "JPEG_R";
            case ImageFormat.RAW_SENSOR: return "RAW_SENSOR";
            case ImageFormat.RAW10: return "RAW10";
            case ImageFormat.RAW12: return "RAW12";
            case ImageFormat.YUV_420_888: return "YUV_420_888";
            case ImageFormat.PRIVATE: return "PRIVATE";
            default: return "FORMAT_" + format;
        }
    }

    static JSONArray sizes(Size[] sizes) throws Exception {
        JSONArray out = new JSONArray();
        if (sizes != null) for (Size size : sizes) out.put(new JSONObject()
                .put("width", size.getWidth()).put("height", size.getHeight()));
        return out;
    }

    static JSONArray sizes(List<Size> sizes) throws Exception {
        return sizes(sizes == null ? null : sizes.toArray(new Size[0]));
    }

    static JSONArray array(Object values) throws Exception {
        JSONArray out = new JSONArray();
        if (values != null) for (int i = 0; i < Array.getLength(values); i++) out.put(Array.get(values, i));
        return out;
    }

    private static String string(Object value) { return value == null ? null : value.toString(); }
}
