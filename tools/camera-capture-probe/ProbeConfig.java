/* SPDX-License-Identifier: Apache-2.0 */
package org.nezha.cameracaptureprobe;

/** Pure configuration validation; no platform calls or camera side effects. */
public final class ProbeConfig {
    public final String cameraId, physicalId, format, pixelMode, streamUseCases;
    public final int width, height;

    public ProbeConfig(String cameraId, String physicalId, String format, int width, int height,
            String pixelMode, String streamUseCases) {
        this.cameraId = identifier(cameraId, false);
        this.physicalId = identifier(physicalId, true);
        if (!"jpeg".equals(format) && !"raw".equals(format) && !"jpeg_r".equals(format)) {
            throw new IllegalArgumentException("format must be jpeg, raw, or jpeg_r");
        }
        if (!"default".equals(pixelMode) && !"maximum".equals(pixelMode)) {
            throw new IllegalArgumentException("pixel_mode must be default or maximum");
        }
        if (!"default".equals(streamUseCases) && !"preview-still".equals(streamUseCases)) {
            throw new IllegalArgumentException("stream_use_cases must be default or preview-still");
        }
        if (width <= 0 || height <= 0 || width > 32768 || height > 32768
                || (long) width * height > 210_000_000L) {
            throw new IllegalArgumentException("Explicit width and height must describe at most 210 MP");
        }
        this.format = format;
        this.width = width;
        this.height = height;
        this.pixelMode = pixelMode;
        this.streamUseCases = streamUseCases;
    }

    private static String identifier(String value, boolean optional) {
        value = value == null ? "" : value.trim();
        if ((value.isEmpty() && !optional) || value.length() > 64
                || (!value.isEmpty() && !value.matches("[A-Za-z0-9_.:-]+"))) {
            throw new IllegalArgumentException("Invalid camera identifier");
        }
        return value;
    }
}
