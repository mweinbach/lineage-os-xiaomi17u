/* SPDX-License-Identifier: Apache-2.0 */
package org.nezha.cameracaptureprobe;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraExtensionCharacteristics;
import android.hardware.camera2.CameraExtensionSession;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.TotalCaptureResult;
import android.hardware.camera2.params.ExtensionSessionConfiguration;
import android.hardware.camera2.params.OutputConfiguration;
import android.media.Image;
import android.media.ImageReader;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.SystemClock;
import android.util.Range;
import android.util.Size;
import android.view.Surface;
import android.view.TextureView;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Executor;

/** One explicit foreground capture through the public CameraExtensionSession API. */
public final class ExtensionCaptureActivity extends Activity implements TextureView.SurfaceTextureListener {
    public static final String ACTION_CAPTURE = "org.nezha.cameracaptureprobe.CAPTURE_EXTENSION";
    private final Handler main = new Handler();
    private HandlerThread thread;
    private Handler worker;
    private TextureView texture;
    private TextView status;
    private EditText cameraId, extensionMode, format, width, height;
    private Button capture;
    private volatile boolean foreground, destroyed;
    private volatile Run current;
    private boolean pendingCapture, permissionPending;
    private int pendingOpenCallbacks; // worker-owned, including cancelled pending opens

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        thread = new HandlerThread("NezhaExtensionCapture");
        thread.start();
        worker = new Handler(thread.getLooper());
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(24, 44, 24, 24);
        TextView title = new TextView(this);
        title.setText("Camera extensions\nOne explicit test captures one image with the selected effect. "
                + "Leaving this screen cancels the test. Unsupported modes are recorded without opening a camera.");
        root.addView(title);
        texture = new TextureView(this);
        texture.setSurfaceTextureListener(this);
        root.addView(texture, new LinearLayout.LayoutParams(-1,
                (int) (180 * getResources().getDisplayMetrics().density)));
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        cameraId = field(content, "Public camera ID", "0");
        extensionMode = field(content, "Extension: auto / face_retouch / bokeh / hdr / night", "auto");
        format = field(content, "Format: jpeg / jpeg_r", "jpeg");
        width = field(content, "Capture width", "4096");
        height = field(content, "Capture height", "3072");
        LinearLayout actions = new LinearLayout(this);
        capture = button(actions, "Capture one", () -> {
            if (current == null) { pendingCapture = true; runPending(); }
        });
        button(actions, "Cancel", () -> { pendingCapture = false; cancelCurrent("explicit_cancel"); });
        content.addView(actions);
        status = new TextView(this);
        status.setTextIsSelectable(true);
        content.addView(status);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        applyIntent(getIntent(), state == null);
        show("Ready. Choose one mode and press Capture one.");
    }

    private EditText field(LinearLayout parent, String name, String value) {
        TextView label = new TextView(this);
        label.setText(name);
        parent.addView(label);
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setText(value);
        parent.addView(input);
        return input;
    }

    private Button button(LinearLayout parent, String name, Runnable action) {
        Button button = new Button(this);
        button.setText(name);
        button.setOnClickListener(v -> action.run());
        parent.addView(button, new LinearLayout.LayoutParams(0, -2, 1));
        return button;
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        cancelCurrent("new_explicit_invocation");
        setIntent(intent);
        applyIntent(intent, true);
        main.post(this::runPending);
    }

    private void applyIntent(Intent intent, boolean allowCapture) {
        if (intent == null) return;
        // Each explicit invocation starts from stated defaults, never a prior form's physical/mode state.
        cameraId.setText(intent.hasExtra("camera_id") ? intent.getStringExtra("camera_id") : "0");
        extensionMode.setText(intent.hasExtra("extension_mode") ? intent.getStringExtra("extension_mode") : "auto");
        format.setText(intent.hasExtra("format") ? intent.getStringExtra("format") : "jpeg");
        width.setText(Integer.toString(intent.getIntExtra("width", 4096)));
        height.setText(Integer.toString(intent.getIntExtra("height", 3072)));
        // No launcher capture or activity-recreation replay. Automated captures must name camera and mode.
        pendingCapture = allowCapture && ACTION_CAPTURE.equals(intent.getAction())
                && intent.getBooleanExtra("capture", false) && intent.hasExtra("camera_id")
                && intent.hasExtra("extension_mode");
    }

    @Override protected void onResume() { super.onResume(); foreground = true; main.post(this::runPending); }
    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);
        if (focused) main.post(this::runPending);
    }
    @Override protected void onPause() {
        foreground = false;
        if (!permissionPending) pendingCapture = false;
        cancelCurrent("activity_paused");
        super.onPause();
    }
    @Override protected void onStop() { pendingCapture = false; super.onStop(); }
    @Override protected void onDestroy() {
        destroyed = true;
        cancelCurrent("activity_destroyed");
        worker.post(this::maybeQuit);
        super.onDestroy();
    }

    private void maybeQuit() {
        if (destroyed && current == null && pendingOpenCallbacks == 0) thread.quitSafely();
    }

    private void runPending() {
        if (!pendingCapture || !foreground || !hasWindowFocus() || current != null || permissionPending) return;
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            permissionPending = true;
            requestPermissions(new String[]{Manifest.permission.CAMERA}, 1);
            return;
        }
        if (!texture.isAvailable()) return;
        pendingCapture = false;
        try {
            ExtensionProbeConfig config = new ExtensionProbeConfig(cameraId.getText().toString(),
                    extensionMode.getText().toString(), format.getText().toString().trim(),
                    Integer.parseInt(width.getText().toString()), Integer.parseInt(height.getText().toString()));
            Run run = new Run(config, texture.getSurfaceTexture());
            current = run;
            capture.setEnabled(false);
            show("Checking " + config.mode + " on camera " + config.cameraId + " for one explicit capture.");
            worker.post(run::start);
        } catch (Exception error) { show("Invalid test: " + error); }
    }

    @Override public void onRequestPermissionsResult(int code, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(code, permissions, grants);
        permissionPending = false;
        if (code == 1 && grants.length == 1 && grants[0] == PackageManager.PERMISSION_GRANTED) main.post(this::runPending);
        else { pendingCapture = false; show("Camera permission denied. No camera opened."); }
    }

    private void cancelCurrent(String reason) {
        Run run = current;
        if (run != null) { run.requestCancellation(reason); worker.post(() -> run.finish("cancelled", reason)); }
    }
    private void show(String value) { main.post(() -> status.setText(value)); }
    @Override public void onSurfaceTextureAvailable(SurfaceTexture surface, int w, int h) { runPending(); }
    @Override public void onSurfaceTextureSizeChanged(SurfaceTexture surface, int w, int h) { }
    @Override public void onSurfaceTextureUpdated(SurfaceTexture surface) {
        Run run = current;
        if (run != null) worker.post(run::previewFrame);
    }
    @Override public boolean onSurfaceTextureDestroyed(SurfaceTexture surface) {
        cancelCurrent("preview_surface_destroyed");
        return true;
    }

    private final class Run {
        final ExtensionProbeConfig config;
        final SurfaceTexture surfaceTexture;
        final int mode, imageFormat;
        final String modeName;
        final File directory;
        final JSONObject report = new JSONObject();
        final JSONArray events = new JSONArray();
        final long started = SystemClock.elapsedRealtime();
        final Executor executor = command -> worker.post(command);
        final Runnable timeout = () -> finish("failed", "60-second extension capture deadline expired");
        volatile boolean active = true;
        boolean finished, waitingForOpen, configured, submitted, processStarted, sequenceCompleted;
        boolean resultMetadataExpected, resultTimestampExpected;
        int previewFrames, captureSequence = -1;
        long firstInputTimestamp;
        String cancellationReason, artifactStage = "not_started";
        CameraDevice device;
        CameraExtensionSession session;
        ImageReader reader;
        Surface preview;
        Image image;
        TotalCaptureResult result;
        File artifact;
        Set<CaptureRequest.Key> requestKeys = Collections.emptySet();

        Run(ExtensionProbeConfig config, SurfaceTexture surfaceTexture) throws Exception {
            this.config = config;
            this.surfaceTexture = surfaceTexture;
            mode = platformMode(config.mode);
            modeName = CameraInventory.extensionName(mode);
            imageFormat = "jpeg_r".equals(config.format) ? ImageFormat.JPEG_R : ImageFormat.JPEG;
            directory = new File(getFilesDir(), "extension-" + System.currentTimeMillis() + "-" + UUID.randomUUID().toString().substring(0, 8));
            if (!directory.mkdir()) throw new IllegalStateException("Cannot create private extension report directory");
            report.put("schema_version", 1).put("api", "CameraExtensionSession").put("package", getPackageName())
                    .put("target_sdk", 36).put("camera_id", config.cameraId).put("extension_name", modeName)
                    .put("extension_mode", mode).put("format", config.format).put("width", config.width)
                    .put("height", config.height).put("requested_captures", 1).put("still_requests_submitted", 0)
                    .put("extension_available", false).put("preview_frame_count", 0)
                    .put("sequence_completed", false).put("process_started", false)
                    .put("result_metadata_expected", false).put("admitted", false).put("events", events);
        }

        boolean live() { return active && !finished && foreground && current == this; }
        synchronized void requestCancellation(String reason) {
            if (!finished) { active = false; if (cancellationReason == null) cancellationReason = reason; }
        }
        void event(String name) {
            try { events.put(new JSONObject().put("name", name).put("elapsed_ms", SystemClock.elapsedRealtime() - started)); }
            catch (Exception ignored) { }
        }

        void start() {
            if (!live()) { finish("cancelled", "Activity not in foreground"); return; }
            worker.postDelayed(timeout, 60_000);
            try {
                CameraManager manager = getSystemService(CameraManager.class);
                String[] ids = manager.getCameraIdList();
                report.put("visible_ids", new JSONArray(ids));
                if (!Arrays.asList(ids).contains(config.cameraId)) throw new IllegalArgumentException("Requested camera is not public to this package");
                CameraExtensionCharacteristics extension = manager.getCameraExtensionCharacteristics(config.cameraId);
                List<Integer> supported = extension.getSupportedExtensions();
                report.put("supported_platform_modes", new JSONArray(supported));
                if (!supported.contains(mode)) { finish("unsupported", "Selected extension is absent from the public supported-mode list"); return; }
                report.put("extension_available", true);
                Size requested = new Size(config.width, config.height);
                List<Size> captureSizes = extension.getExtensionSupportedSizes(mode, imageFormat);
                report.put("advertised_capture_sizes", CameraInventory.sizes(captureSizes));
                if (captureSizes == null || !captureSizes.contains(requested)) {
                    finish("unsupported", "Exact extension format/dimensions are not advertised"); return;
                }
                List<Size> previewSizes = extension.getExtensionSupportedSizes(mode, SurfaceTexture.class);
                report.put("advertised_preview_sizes", CameraInventory.sizes(previewSizes));
                Size previewSize = selectPreview(previewSizes, requested);
                report.put("preview_width", previewSize.getWidth()).put("preview_height", previewSize.getHeight());
                requestKeys = extension.getAvailableCaptureRequestKeys(mode);
                JSONArray requestNames = new JSONArray();
                for (CaptureRequest.Key key : requestKeys) requestNames.put(key.getName());
                report.put("available_request_keys", requestNames);
                Set<CaptureResult.Key> resultKeys = extension.getAvailableCaptureResultKeys(mode);
                JSONArray resultNames = new JSONArray();
                for (CaptureResult.Key key : resultKeys) resultNames.put(key.getName());
                resultMetadataExpected = !resultKeys.isEmpty();
                resultTimestampExpected = resultKeys.contains(CaptureResult.SENSOR_TIMESTAMP);
                report.put("available_result_keys", resultNames).put("result_metadata_expected", resultMetadataExpected)
                        .put("result_timestamp_expected", resultTimestampExpected);
                // The receipt requires a trustworthy image/result association when metadata is advertised.
                if (resultMetadataExpected && !resultTimestampExpected) {
                    finish("unsupported", "Extension result metadata lacks SENSOR_TIMESTAMP required for receipt association"); return;
                }
                try { report.put("postview_available", extension.isPostviewAvailable(mode)); }
                catch (Exception error) { report.put("postview_query_error", error.toString()); }
                try { report.put("capture_progress_available", extension.isCaptureProcessProgressAvailable(mode)); }
                catch (Exception error) { report.put("capture_progress_query_error", error.toString()); }
                try {
                    Range<Long> latency = extension.getEstimatedCaptureLatencyRangeMillis(mode, requested, imageFormat);
                    if (latency != null) report.put("estimated_latency_min_ms", latency.getLower()).put("estimated_latency_max_ms", latency.getUpper());
                } catch (Exception error) { report.put("latency_query_error", error.toString()); }
                surfaceTexture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
                preview = new Surface(surfaceTexture);
                reader = ImageReader.newInstance(config.width, config.height, imageFormat, 2);
                reader.setOnImageAvailableListener(this::onImage, worker);
                event("extension_configuration_admitted_from_public_api");
                writeJson(new File(directory, "report.json"), report);
                if (!live()) { finish("cancelled", "Activity left foreground during discovery"); return; }
                waitingForOpen = true;
                pendingOpenCallbacks++;
                manager.openCamera(config.cameraId, new CameraDevice.StateCallback() {
                    @Override public void onOpened(CameraDevice opened) {
                        completeOpen();
                        if (!live()) { opened.close(); maybeQuit(); return; }
                        device = opened;
                        event("camera_opened");
                        configure();
                    }
                    @Override public void onDisconnected(CameraDevice disconnected) {
                        completeOpen(); disconnected.close(); finish("failed", "camera_disconnected"); maybeQuit();
                    }
                    @Override public void onError(CameraDevice failed, int error) {
                        completeOpen(); failed.close(); finish("failed", "camera_device_error_" + error); maybeQuit();
                    }
                }, worker);
            } catch (Exception error) { completeOpen(); finish("unsupported_or_failed", "discovery/open: " + error); }
        }

        void completeOpen() { if (waitingForOpen) { waitingForOpen = false; pendingOpenCallbacks--; } }
        void configure() {
            if (!live()) { finish("cancelled", "Activity not in foreground"); return; }
            try {
                ExtensionSessionConfiguration configuration = new ExtensionSessionConfiguration(mode,
                        Arrays.asList(new OutputConfiguration(preview), new OutputConfiguration(reader.getSurface())),
                        executor, new CameraExtensionSession.StateCallback() {
                    @Override public void onConfigured(CameraExtensionSession ready) {
                        if (!live()) { closeLateSession(ready); return; }
                        session = ready; configured = true;
                        event("extension_session_configured");
                        startPreview();
                    }
                    @Override public void onConfigureFailed(CameraExtensionSession failed) {
                        closeLateSession(failed); finish("failed", "extension_session_configuration_failed");
                    }
                    @Override public void onClosed(CameraExtensionSession closed) {
                        if (live() && session == closed) finish("failed", "extension_session_closed_before_completion");
                    }
                });
                device.createExtensionSession(configuration);
            } catch (Exception error) { finish("failed", "extension configure: " + error); }
        }

        void startPreview() {
            try {
                CaptureRequest.Builder builder = device.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                builder.addTarget(preview);
                session.setRepeatingRequest(builder.build(), executor, new CameraExtensionSession.ExtensionCaptureCallback() {
                    @Override public void onCaptureFailed(CameraExtensionSession s, CaptureRequest request) {
                        if (live() && !submitted) finish("failed", "extension_preview_failed");
                    }
                    @Override public void onCaptureFailed(CameraExtensionSession s, CaptureRequest request, int reason) {
                        if (live() && !submitted) finish("failed", "extension_preview_failed_" + reason);
                    }
                });
                show("Waiting for eight visible " + modeName + " preview frames before one still capture.");
            } catch (Exception error) { finish("failed", "extension preview: " + error); }
        }

        void previewFrame() {
            if (!live() || !configured || submitted) return;
            previewFrames++;
            if (previewFrames == 1) event("first_visible_preview_frame");
            if (previewFrames >= 8) captureOnce();
        }

        void captureOnce() {
            if (!live() || submitted) return;
            submitted = true;
            try {
                CaptureRequest.Builder builder = device.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
                // Extension still captures target only the still surface; no ordinary preview/still request pair.
                builder.addTarget(reader.getSurface());
                if (requestKeys.contains(CaptureRequest.JPEG_QUALITY)) builder.set(CaptureRequest.JPEG_QUALITY, (byte) 95);
                session.stopRepeating();
                event("one_extension_still_request_submitted");
                captureSequence = session.capture(builder.build(), executor, new CameraExtensionSession.ExtensionCaptureCallback() {
                    @Override public void onCaptureStarted(CameraExtensionSession s, CaptureRequest request, long timestamp) {
                        if (!live()) return;
                        firstInputTimestamp = timestamp;
                        event("extension_capture_started");
                    }
                    @Override public void onCaptureProcessStarted(CameraExtensionSession s, CaptureRequest request) {
                        if (!live()) return;
                        processStarted = true;
                        event("extension_processing_started");
                        maybeSave();
                    }
                    @Override public void onCaptureResultAvailable(CameraExtensionSession s, CaptureRequest request, TotalCaptureResult total) {
                        if (!live()) return;
                        result = total;
                        event("extension_total_result_received");
                        maybeSave();
                    }
                    @Override public void onCaptureSequenceCompleted(CameraExtensionSession s, int sequence) {
                        if (!live()) return;
                        if (sequence != captureSequence) { finish("failed", "Unexpected extension capture sequence ID"); return; }
                        sequenceCompleted = true;
                        event("extension_sequence_completed");
                        maybeSave();
                    }
                    @Override public void onCaptureSequenceAborted(CameraExtensionSession s, int sequence) {
                        if (live()) finish("failed", "extension_sequence_aborted_" + sequence);
                    }
                    @Override public void onCaptureFailed(CameraExtensionSession s, CaptureRequest request) {
                        if (live()) finish("failed", "extension_still_failed");
                    }
                    @Override public void onCaptureFailed(CameraExtensionSession s, CaptureRequest request, int reason) {
                        if (live()) finish("failed", "extension_still_failed_" + reason);
                    }
                    @Override public void onCaptureProcessProgressed(CameraExtensionSession s, CaptureRequest request, int progress) {
                        if (live()) event("extension_processing_progress_" + progress);
                    }
                });
                report.put("capture_sequence_id", captureSequence).put("still_requests_submitted", 1)
                        .put("preview_frame_count", previewFrames);
            } catch (Exception error) { finish("failed", "extension still capture: " + error); }
        }

        void onImage(ImageReader source) {
            Image received = null;
            try {
                received = source.acquireNextImage();
                if (received == null) return;
                if (!live() || !submitted || image != null) { received.close(); return; }
                image = received;
                event("extension_image_received");
                maybeSave();
            } catch (Exception error) {
                if (received != null && received != image) received.close();
                if (live()) finish("failed", "extension image: " + error);
            }
        }

        void maybeSave() {
            if (!live() || image == null || !processStarted || !sequenceCompleted
                    || (resultMetadataExpected && result == null)) return;
            try {
                report.put("process_started", processStarted).put("sequence_completed", sequenceCompleted)
                        .put("image_timestamp_ns", image.getTimestamp()).put("first_input_timestamp_ns", firstInputTimestamp);
                if (image.getFormat() != imageFormat || image.getWidth() != config.width || image.getHeight() != config.height) {
                    throw new IllegalStateException("Returned extension image format/dimensions differ from explicit request");
                }
                if (resultMetadataExpected) {
                    Long timestamp = result.get(CaptureResult.SENSOR_TIMESTAMP);
                    report.put("result_timestamp_ns", timestamp);
                    boolean match = timestamp != null && timestamp > 0 && timestamp.longValue() == image.getTimestamp();
                    report.put("timestamp_match", match);
                    if (!match) throw new IllegalStateException("Extension image/result timestamps do not match");
                } else {
                    report.put("metadata_association", "Public API advertises no result metadata; one extension still request with completed processing and sequence")
                            .put("unexpected_result_metadata_received", result != null);
                }
                event("camera_closed_before_file_processing");
                closeCamera();
                if (!live()) { finish("cancelled", "Cancelled before extension image write"); return; }
                artifact = new File(directory, "capture.jpg");
                artifactStage = "writing";
                try (FileOutputStream output = new FileOutputStream(artifact)) {
                    ByteBuffer bytes = image.getPlanes()[0].getBuffer();
                    byte[] buffer = new byte[64 * 1024];
                    while (bytes.hasRemaining()) {
                        if (!live()) throw new java.util.concurrent.CancellationException("Cancelled during extension image write");
                        int count = Math.min(bytes.remaining(), buffer.length);
                        bytes.get(buffer, 0, count); output.write(buffer, 0, count);
                    }
                }
                artifactStage = "written";
                if (!live()) { finish("cancelled", "Cancelled during extension image write"); return; }
                report.put("file_name", artifact.getName()).put("file_bytes", artifact.length()).put("file_sha256", sha256(artifact));
                if (!live()) { finish("cancelled", "Cancelled during extension image hashing"); return; }
                artifactStage = "validating";
                verifyJpeg(artifact);
                artifactStage = "validated";
                if (!live()) { finish("cancelled", "Cancelled during extension image validation"); return; }
                event("extension_file_saved");
                finish("captured", "One validated extension image saved; independent host pixel/gain-map review remains required");
            } catch (Exception error) { finish(live() ? "failed" : "cancelled", "extension save: " + error); }
        }

        void verifyJpeg(File file) throws Exception {
            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(file.getAbsolutePath(), bounds);
            report.put("jpeg_width", bounds.outWidth).put("jpeg_height", bounds.outHeight).put("encoded_mime_type", bounds.outMimeType);
            if (!"image/jpeg".equals(bounds.outMimeType) || bounds.outWidth != config.width || bounds.outHeight != config.height) {
                throw new IllegalStateException("Encoded extension JPEG type/dimensions differ from explicit request");
            }
            BitmapFactory.Options sample = new BitmapFactory.Options();
            sample.inSampleSize = 1;
            while ((long) bounds.outWidth * bounds.outHeight / sample.inSampleSize / sample.inSampleSize > 4_000_000L) sample.inSampleSize *= 2;
            Bitmap bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), sample);
            if (bitmap == null) throw new IllegalStateException("Extension JPEG failed pixel decode");
            try {
                report.put("jpeg_decoded", true).put("jpeg_decode_sample_size", sample.inSampleSize).put("has_gainmap", bitmap.hasGainmap());
                if (imageFormat == ImageFormat.JPEG_R && !bitmap.hasGainmap()) throw new IllegalStateException("JPEG_R extension output lacks a decoded gain map");
            } finally { bitmap.recycle(); }
        }

        void closeLateSession(CameraExtensionSession closing) {
            try { closing.close(); } catch (Exception ignored) { }
        }
        void closeCamera() {
            CameraExtensionSession closing = session;
            session = null;
            if (closing != null) {
                try { closing.close(); } catch (Exception error) { event("extension_session_close_error_" + error.getClass().getSimpleName()); }
            }
            if (device != null) { device.close(); device = null; }
        }
        void finish(String outcome, String detail) {
            synchronized (this) {
                if (finished) return;
                if (cancellationReason != null || ("captured".equals(outcome) && (!active || !foreground || current != this))) {
                    outcome = "cancelled";
                    detail = cancellationReason == null ? "Activity left foreground before extension finalization" : cancellationReason;
                }
                finished = true; active = false;
            }
            worker.removeCallbacks(timeout);
            event("extension_resources_closing");
            closeCamera();
            if (image != null) { image.close(); image = null; }
            if (reader != null) { reader.close(); reader = null; }
            if (preview != null) { preview.release(); preview = null; }
            try {
                if (!"captured".equals(outcome) && artifact != null && artifact.isFile()) {
                    JSONObject partial = new JSONObject().put("file_name", artifact.getName()).put("file_bytes", artifact.length())
                            .put("stage", artifactStage).put("admitted", false);
                    try { partial.put("file_sha256", sha256(artifact)); } catch (Exception error) { partial.put("hash_error", error.toString()); }
                    report.put("partial_artifact", partial);
                }
                report.put("outcome", outcome).put("detail", detail).put("admitted", "captured".equals(outcome))
                        .put("preview_frame_count", previewFrames).put("process_started", processStarted)
                        .put("sequence_completed", sequenceCompleted).put("elapsed_ms", SystemClock.elapsedRealtime() - started);
                writeJson(new File(directory, "report.json"), report);
                show(outcome + ": " + detail + "\nPrivate report: " + directory.getName() + "/report.json\n" + report.toString(2));
            } catch (Exception error) { show("Unable to save extension report: " + error); }
            if (current == this) current = null;
            main.post(() -> { capture.setEnabled(true); runPending(); });
            maybeQuit();
        }
    }

    private static int platformMode(String mode) {
        switch (mode) {
            case "auto": return CameraExtensionCharacteristics.EXTENSION_AUTOMATIC;
            case "face_retouch": return CameraExtensionCharacteristics.EXTENSION_FACE_RETOUCH;
            case "bokeh": return CameraExtensionCharacteristics.EXTENSION_BOKEH;
            case "hdr": return CameraExtensionCharacteristics.EXTENSION_HDR;
            case "night": return CameraExtensionCharacteristics.EXTENSION_NIGHT;
            default: throw new IllegalArgumentException("Unknown extension mode");
        }
    }
    private static Size selectPreview(List<Size> values, Size still) {
        Size best = null;
        double score = Double.MAX_VALUE;
        if (values != null) for (Size size : values) {
            if (size.getWidth() > 1920 || size.getHeight() > 1920 || (long) size.getWidth() * size.getHeight() > 1920L * 1080) continue;
            double candidate = Math.abs((double) size.getWidth() / size.getHeight() - (double) still.getWidth() / still.getHeight())
                    * 10_000_000 - (long) size.getWidth() * size.getHeight();
            if (candidate < score) { best = size; score = candidate; }
        }
        if (best == null) throw new IllegalArgumentException("No advertised extension preview size within 1920x1080 area");
        return best;
    }
    private static void writeJson(File file, JSONObject json) throws Exception {
        try (FileOutputStream output = new FileOutputStream(file)) { output.write((json.toString(2) + "\n").getBytes(StandardCharsets.UTF_8)); }
    }
    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (FileInputStream input = new FileInputStream(file)) {
            byte[] bytes = new byte[64 * 1024];
            int count;
            while ((count = input.read(bytes)) != -1) digest.update(bytes, 0, count);
        }
        StringBuilder result = new StringBuilder();
        for (byte value : digest.digest()) result.append(String.format("%02x", value & 0xff));
        return result.toString();
    }
}
