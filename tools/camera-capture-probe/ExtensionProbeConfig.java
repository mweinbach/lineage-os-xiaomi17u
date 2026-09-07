/* SPDX-License-Identifier: Apache-2.0 */
package org.nezha.cameracaptureprobe;

/** Validates an explicit extension capture without opening a camera. */
public final class ExtensionProbeConfig {
    public final String cameraId, mode, format;
    public final int width, height;

    public ExtensionProbeConfig(String cameraId, String mode, String format, int width, int height) {
        ProbeConfig validated = new ProbeConfig(cameraId, "", format, width, height, "default", "default");
        if (!"jpeg".equals(format) && !"jpeg_r".equals(format)) {
            throw new IllegalArgumentException("Extension format must be jpeg or jpeg_r");
        }
        mode = mode == null ? "" : mode.trim().toLowerCase(java.util.Locale.ROOT);
        if ("automatic".equals(mode)) mode = "auto";
        if ("beauty".equals(mode)) mode = "face_retouch";
        if (!"auto".equals(mode) && !"face_retouch".equals(mode) && !"bokeh".equals(mode)
                && !"hdr".equals(mode) && !"night".equals(mode)) {
            throw new IllegalArgumentException("extension_mode must be auto, face_retouch, bokeh, hdr, or night; numeric CameraX modes are not accepted");
        }
        this.cameraId = validated.cameraId;
        this.mode = mode;
        this.format = format;
        this.width = width;
        this.height = height;
    }
}
