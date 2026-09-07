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
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureFailure;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.DngCreator;
import android.hardware.camera2.TotalCaptureResult;
import android.hardware.camera2.params.OutputConfiguration;
import android.hardware.camera2.params.SessionConfiguration;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.SystemClock;
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
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executor;

/** Foreground, one-shot Camera2 diagnostics. No service, network, or device-setting changes. */
public final class CaptureActivity extends Activity implements TextureView.SurfaceTextureListener {
    public static final String ACTION_CAPTURE = "org.nezha.cameracaptureprobe.CAPTURE_TEST";
    public static final String ACTION_INSPECT = "org.nezha.cameracaptureprobe.INSPECT";
    private final Handler main = new Handler();
    private HandlerThread thread;
    private Handler worker;
    private TextureView texture;
    private TextView status;
    private EditText cameraId, physicalId, format, width, height, pixelMode, streamUseCases;
    private Button inspect, capture, cancel;
    private volatile boolean foreground;
    private volatile Run current;
    private volatile boolean destroyed;
    // Worker-owned count: retain the callback looper until a pending open can be closed.
    private int pendingOpenCallbacks;
    private boolean pendingCapture, pendingInspect, permissionPending;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        thread = new HandlerThread("NezhaCaptureProbe");
        thread.start();
        worker = new Handler(thread.getLooper());
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(24, 44, 24, 24);
        TextView title = new TextView(this);
        title.setText("Camera capture probe\nOne explicit test saves one image and its report "
                + "in this app's private files. Leaving this screen cancels the camera session.");
        root.addView(title);
        // The preview stays visible while the controls/report scroll underneath it.
        texture = new TextureView(this);
        texture.setSurfaceTextureListener(this);
        root.addView(texture, new LinearLayout.LayoutParams(-1,
                (int) (180 * getResources().getDisplayMetrics().density)));
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        cameraId = field(content, "Camera ID", "0");
        physicalId = field(content, "Physical ID (optional child of logical camera)", "");
        format = field(content, "Format: jpeg / raw / jpeg_r", "jpeg");
        width = field(content, "Capture width", "4096");
        height = field(content, "Capture height", "3072");
        pixelMode = field(content, "Pixel mode: default / maximum", "default");
        streamUseCases = field(content, "Stream use cases: default / preview-still", "default");
        LinearLayout actions = new LinearLayout(this);
        inspect = button(actions, "Inspect", () -> requestAction(false));
        capture = button(actions, "Capture one", () -> requestAction(true));
        cancel = button(actions, "Cancel", () -> {
            pendingCapture = pendingInspect = false;
            cancelCurrent("explicit_cancel");
        });
        content.addView(actions);
        LinearLayout extensionActions = new LinearLayout(this);
        button(extensionActions, "Extensions", () -> {
            if (current != null || !inspect.isEnabled()) {
                show("Finish or cancel the current test before opening extensions.");
                return;
            }
            pendingCapture = pendingInspect = false;
            startActivity(new Intent(this, ExtensionCaptureActivity.class));
        });
        content.addView(extensionActions);
        status = new TextView(this);
        status.setTextIsSelectable(true);
        content.addView(status);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        applyIntent(getIntent(), state == null);
        show("Ready. Inspect reads metadata. Capture one opens only the specified camera.");
    }

    private EditText field(LinearLayout parent, String label, String value) {
        TextView name = new TextView(this);
        name.setText(label);
        parent.addView(name);
        EditText field = new EditText(this);
        field.setSingleLine(true);
        field.setText(value);
        parent.addView(field);
        return field;
    }

    private Button button(LinearLayout parent, String label, Runnable action) {
        Button button = new Button(this);
        button.setText(label);
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

    private void applyIntent(Intent intent, boolean allowAction) {
        if (intent == null) return;
        EditText[] fields = {cameraId, physicalId, format, width, height, pixelMode, streamUseCases};
        String[] names = {"camera_id", "physical_id", "format", "width", "height", "pixel_mode", "stream_use_cases"};
        for (int i = 0; i < names.length; i++) {
            if (intent.hasExtra(names[i])) {
                if ("width".equals(names[i]) || "height".equals(names[i])) {
                    fields[i].setText(Integer.toString(intent.getIntExtra(names[i], 0)));
                } else fields[i].setText(intent.getStringExtra(names[i]));
            }
        }
        // Recreation never replays an earlier capture. The custom action and explicit flag are both required.
        pendingCapture = allowAction && ACTION_CAPTURE.equals(intent.getAction())
                && intent.getBooleanExtra("capture", false);
        pendingInspect = allowAction && ACTION_INSPECT.equals(intent.getAction());
    }

    @Override protected void onResume() {
        super.onResume();
        foreground = true;
        main.post(this::runPending);
    }

    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);
        if (focused) main.post(this::runPending);
    }

    @Override protected void onPause() {
        foreground = false;
        // Only our outstanding permission dialog may retain an explicit pending action.
        // Every other interruption requires a fresh button press or explicit invocation.
        if (!permissionPending) pendingCapture = pendingInspect = false;
        cancelCurrent("activity_paused");
        super.onPause();
    }

    @Override protected void onStop() {
        // Going fully out of view disarms even a request whose permission dialog was open.
        pendingCapture = pendingInspect = false;
        super.onStop();
    }

    @Override protected void onDestroy() {
        destroyed = true;
        cancelCurrent("activity_destroyed");
        worker.post(this::maybeQuit);
        super.onDestroy();
    }

    private void maybeQuit() {
        if (destroyed && current == null && pendingOpenCallbacks == 0) thread.quitSafely();
    }

    private void requestAction(boolean takePhoto) {
        if (current != null) { show("A test is already running."); return; }
        pendingCapture = takePhoto;
        pendingInspect = !takePhoto;
        runPending();
    }

    private void runPending() {
        if ((!pendingCapture && !pendingInspect) || !foreground || !hasWindowFocus()
                || current != null || permissionPending) return;
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            permissionPending = true;
            requestPermissions(new String[]{Manifest.permission.CAMERA}, 1);
            return;
        }
        if (pendingCapture && !texture.isAvailable()) return;
        boolean takePhoto = pendingCapture;
        pendingCapture = pendingInspect = false;
        if (!takePhoto) {
            inspect.setEnabled(false);
            capture.setEnabled(false);
            worker.post(this::inspectMetadata);
            return;
        }
        try {
            ProbeConfig config = new ProbeConfig(cameraId.getText().toString(), physicalId.getText().toString(),
                    format.getText().toString().trim(), Integer.parseInt(width.getText().toString()),
                    Integer.parseInt(height.getText().toString()), pixelMode.getText().toString().trim(),
                    streamUseCases.getText().toString().trim());
            Run run = new Run(config, texture.getSurfaceTexture());
            current = run;
            inspect.setEnabled(false);
            capture.setEnabled(false);
            show("Starting one " + config.format + " capture on camera " + config.cameraId + ".");
            worker.post(run::start);
        } catch (Exception error) { show("Invalid test: " + error); }
    }

    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(request, permissions, grants);
        permissionPending = false;
        if (request == 1 && grants.length == 1 && grants[0] == PackageManager.PERMISSION_GRANTED) {
            main.post(this::runPending);
        } else {
            pendingCapture = pendingInspect = false;
            show("Camera permission denied. No camera opened.");
        }
    }

    private void inspectMetadata() {
        JSONObject report = new JSONObject();
        File output = new File(getFilesDir(), "inventory-" + System.currentTimeMillis() + ".json");
        try {
            report = CameraInventory.inspect(getSystemService(CameraManager.class));
            report.put("schema_version", 1).put("package", getPackageName()).put("target_sdk", 36)
                    .put("capture_performed", false);
            writeJson(output, report);
            show("Metadata saved: " + output.getName() + "\n" + report.toString(2));
        } catch (Exception error) { show("Metadata inspection failed: " + error); }
        main.post(() -> { inspect.setEnabled(true); capture.setEnabled(true); });
    }

    private void cancelCurrent(String reason) {
        Run run = current;
        if (run != null) {
            run.requestCancellation(reason);
            worker.post(() -> run.finish("cancelled", reason));
        }
    }

    private void show(String value) { main.post(() -> status.setText(value)); }

    @Override public void onSurfaceTextureAvailable(SurfaceTexture surface, int w, int h) { runPending(); }
    @Override public void onSurfaceTextureSizeChanged(SurfaceTexture surface, int w, int h) { }
    @Override public void onSurfaceTextureUpdated(SurfaceTexture surface) { }
    @Override public boolean onSurfaceTextureDestroyed(SurfaceTexture surface) {
        cancelCurrent("preview_surface_destroyed");
        return true;
    }

    private final class Run {
        final ProbeConfig config;
        final SurfaceTexture surfaceTexture;
        final File directory;
        final JSONObject report = new JSONObject();
        final JSONArray events = new JSONArray();
        final long started = SystemClock.elapsedRealtime();
        final Executor executor = command -> worker.post(command);
        final Runnable timeout = () -> finish("failed", "25-second camera deadline expired");
        volatile boolean active = true;
        boolean finished, submitted, waitingForOpen;
        String cancellationReason;
        File artifact;
        String artifactStage = "not_started";
        CameraCharacteristics characteristics;
        CameraDevice device;
        CameraCaptureSession session;
        ImageReader reader;
        Surface preview;
        Image image;
        TotalCaptureResult result;
        int formatValue, pixelModeValue, previewFrames;

        Run(ProbeConfig config, SurfaceTexture surfaceTexture) throws Exception {
            this.config = config;
            this.surfaceTexture = surfaceTexture;
            directory = new File(getFilesDir(), "capture-" + System.currentTimeMillis()
                    + "-" + UUID.randomUUID().toString().substring(0, 8));
            if (!directory.mkdir()) throw new IllegalStateException("Cannot create private test directory");
            report.put("schema_version", 1).put("package", getPackageName()).put("target_sdk", 36)
                    .put("camera_id", config.cameraId).put("physical_id", config.physicalId)
                    .put("format", config.format).put("width", config.width).put("height", config.height)
                    .put("pixel_mode", config.pixelMode).put("stream_use_cases", config.streamUseCases)
                    .put("requested_captures", 1).put("events", events);
        }

        boolean live() { return active && !finished && foreground && current == this; }

        synchronized void requestCancellation(String reason) {
            if (!finished) {
                active = false;
                if (cancellationReason == null) cancellationReason = reason;
            }
        }

        void event(String name) {
            try { events.put(new JSONObject().put("name", name)
                    .put("elapsed_ms", SystemClock.elapsedRealtime() - started)); }
            catch (Exception ignored) { }
        }

        void start() {
            if (!live()) { finish("cancelled", "Activity not in foreground"); return; }
            worker.postDelayed(timeout, 25_000);
            try {
                CameraManager manager = getSystemService(CameraManager.class);
                String[] ids = manager.getCameraIdList();
                report.put("visible_ids", new JSONArray(ids));
                if (!Arrays.asList(ids).contains(config.cameraId)) {
                    throw new IllegalArgumentException("Requested camera_id is not in this package's visible ID list");
                }
                CameraCharacteristics logical = manager.getCameraCharacteristics(config.cameraId);
                if (!config.physicalId.isEmpty() && !logical.getPhysicalCameraIds().contains(config.physicalId)) {
                    throw new IllegalArgumentException("physical_id is not a child of camera_id");
                }
                characteristics = config.physicalId.isEmpty() ? logical
                        : manager.getCameraCharacteristics(config.physicalId);
                report.put("lens_facing", characteristics.get(CameraCharacteristics.LENS_FACING))
                        .put("focal_lengths", CameraInventory.array(characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)))
                        .put("capabilities", CameraInventory.array(characteristics.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)));
                formatValue = "raw".equals(config.format) ? ImageFormat.RAW_SENSOR
                        : "jpeg_r".equals(config.format) ? ImageFormat.JPEG_R : ImageFormat.JPEG;
                if (formatValue == ImageFormat.RAW_SENSOR && !contains(characteristics.get(
                        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES), CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_RAW)) {
                    throw new IllegalArgumentException("RAW capability is absent");
                }
                boolean maximum = "maximum".equals(config.pixelMode);
                pixelModeValue = maximum ? CaptureRequest.SENSOR_PIXEL_MODE_MAXIMUM_RESOLUTION
                        : CaptureRequest.SENSOR_PIXEL_MODE_DEFAULT;
                if (maximum && !contains(characteristics.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES),
                        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_ULTRA_HIGH_RESOLUTION_SENSOR)) {
                    throw new IllegalArgumentException("ULTRA_HIGH_RESOLUTION_SENSOR capability is absent; vendor-only sizes are not standard maximum-resolution support");
                }
                StreamConfigurationMap map = characteristics.get(maximum
                        ? CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP_MAXIMUM_RESOLUTION
                        : CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                Size requested = new Size(config.width, config.height);
                if (map == null || (!contains(map.getOutputSizes(formatValue), requested)
                        && !contains(map.getHighResolutionOutputSizes(formatValue), requested))) {
                    throw new IllegalArgumentException("Exact format/dimensions are absent from the selected public stream map");
                }
                StreamConfigurationMap normal = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                Size previewSize = selectPreview(normal == null ? null : normal.getOutputSizes(SurfaceTexture.class), requested);
                report.put("preview_width", previewSize.getWidth()).put("preview_height", previewSize.getHeight());
                if ("preview-still".equals(config.streamUseCases)) {
                    long[] cases = logical.get(CameraCharacteristics.SCALER_AVAILABLE_STREAM_USE_CASES);
                    if (!contains(cases, CameraCharacteristics.SCALER_AVAILABLE_STREAM_USE_CASES_PREVIEW)
                            || !contains(cases, CameraCharacteristics.SCALER_AVAILABLE_STREAM_USE_CASES_STILL_CAPTURE)) {
                        throw new IllegalArgumentException("PREVIEW/STILL_CAPTURE stream use cases are not advertised");
                    }
                }
                surfaceTexture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
                preview = new Surface(surfaceTexture);
                reader = ImageReader.newInstance(config.width, config.height, formatValue, 2);
                reader.setOnImageAvailableListener(this::onImage, worker);
                event("configuration_admitted_from_public_metadata");
                writeJson(new File(directory, "report.json"), report);
                if (!live()) { finish("cancelled", "Activity left foreground during validation"); return; }
                waitingForOpen = true;
                pendingOpenCallbacks++;
                manager.openCamera(config.cameraId, new CameraDevice.StateCallback() {
                    @Override public void onOpened(CameraDevice opened) {
                        completeOpenCallback();
                        if (!live()) { opened.close(); maybeQuit(); return; }
                        device = opened;
                        event("camera_opened");
                        configure();
                    }
                    @Override public void onDisconnected(CameraDevice disconnected) {
                        completeOpenCallback();
                        disconnected.close();
                        finish("failed", "camera_disconnected");
                        maybeQuit();
                    }
                    @Override public void onError(CameraDevice failedDevice, int error) {
                        completeOpenCallback();
                        failedDevice.close();
                        finish("failed", "camera_device_error_" + error);
                        maybeQuit();
                    }
                }, worker);
            } catch (Exception error) {
                completeOpenCallback();
                finish("unsupported_or_failed", error.toString());
            }
        }

        void completeOpenCallback() {
            if (waitingForOpen) {
                waitingForOpen = false;
                pendingOpenCallbacks--;
            }
        }

        void configure() {
            if (!live()) { finish("cancelled", "Activity not in foreground"); return; }
            try {
                OutputConfiguration previewOutput = new OutputConfiguration(preview);
                OutputConfiguration stillOutput = new OutputConfiguration(reader.getSurface());
                if (!config.physicalId.isEmpty()) {
                    previewOutput.setPhysicalCameraId(config.physicalId);
                    stillOutput.setPhysicalCameraId(config.physicalId);
                }
                if (pixelModeValue == CaptureRequest.SENSOR_PIXEL_MODE_MAXIMUM_RESOLUTION) {
                    stillOutput.addSensorPixelModeUsed(pixelModeValue);
                }
                if ("preview-still".equals(config.streamUseCases)) {
                    previewOutput.setStreamUseCase(CameraCharacteristics.SCALER_AVAILABLE_STREAM_USE_CASES_PREVIEW);
                    stillOutput.setStreamUseCase(CameraCharacteristics.SCALER_AVAILABLE_STREAM_USE_CASES_STILL_CAPTURE);
                }
                SessionConfiguration configuration = new SessionConfiguration(SessionConfiguration.SESSION_REGULAR,
                        Arrays.asList(previewOutput, stillOutput), executor, new CameraCaptureSession.StateCallback() {
                    @Override public void onConfigured(CameraCaptureSession configured) {
                        if (!live()) { configured.close(); return; }
                        session = configured;
                        event("session_configured");
                        startPreview();
                    }
                    @Override public void onConfigureFailed(CameraCaptureSession failedSession) {
                        failedSession.close();
                        finish("failed", "session_configuration_failed");
                    }
                });
                try { report.put("is_session_configuration_supported", device.isSessionConfigurationSupported(configuration)); }
                catch (UnsupportedOperationException error) { report.put("session_support_query", "unavailable"); }
                // false is an actual rejection, not permission to try an unadvertised combination.
                if (report.has("is_session_configuration_supported")
                        && !report.getBoolean("is_session_configuration_supported")) {
                    finish("unsupported", "Exact session combination rejected by support query");
                    return;
                }
                device.createCaptureSession(configuration);
            } catch (Exception error) { finish("failed", "configure: " + error); }
        }

        void startPreview() {
            try {
                CaptureRequest.Builder builder = device.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                builder.addTarget(preview);
                autoControls(builder);
                session.setRepeatingRequest(builder.build(), new CameraCaptureSession.CaptureCallback() {
                    @Override public void onCaptureCompleted(CameraCaptureSession s, CaptureRequest request, TotalCaptureResult r) {
                        if (!live() || submitted) return;
                        previewFrames++;
                        if (previewFrames == 1) event("first_preview_result");
                        if (previewFrames >= 8) captureOnce();
                    }
                    @Override public void onCaptureFailed(CameraCaptureSession s, CaptureRequest request, CaptureFailure failure) {
                        if (live() && !submitted) finish("failed", "preview_capture_failed_" + failure.getReason());
                    }
                }, worker);
                show("Visible preview is warming up for one " + config.format + " capture.");
            } catch (Exception error) { finish("failed", "preview: " + error); }
        }

        void autoControls(CaptureRequest.Builder builder) {
            builder.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
            builder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON);
            int[] modes = characteristics.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES);
            if (contains(modes, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE)) {
                builder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
            }
        }

        void captureOnce() {
            if (!live() || submitted) return;
            submitted = true;
            try {
                CaptureRequest.Builder builder = device.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
                builder.addTarget(reader.getSurface());
                if (pixelModeValue == CaptureRequest.SENSOR_PIXEL_MODE_DEFAULT) builder.addTarget(preview);
                autoControls(builder);
                List<CaptureRequest.Key<?>> keys = characteristics.getAvailableCaptureRequestKeys();
                if (keys != null && keys.contains(CaptureRequest.SENSOR_PIXEL_MODE)) {
                    builder.set(CaptureRequest.SENSOR_PIXEL_MODE, pixelModeValue);
                } else if (pixelModeValue != CaptureRequest.SENSOR_PIXEL_MODE_DEFAULT) {
                    throw new IllegalArgumentException("Sensor pixel mode request key is absent");
                }
                if (formatValue == ImageFormat.RAW_SENSOR) {
                    if (contains(characteristics.get(CameraCharacteristics.STATISTICS_INFO_AVAILABLE_LENS_SHADING_MAP_MODES),
                            CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE_ON)) {
                        builder.set(CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE, CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE_ON);
                    }
                } else builder.set(CaptureRequest.JPEG_QUALITY, (byte) 95);
                session.stopRepeating();
                event("one_still_request_submitted");
                int sequence = session.capture(builder.build(), new CameraCaptureSession.CaptureCallback() {
                    @Override public void onCaptureCompleted(CameraCaptureSession s, CaptureRequest request, TotalCaptureResult total) {
                        if (!live()) return;
                        if (!config.physicalId.isEmpty()) {
                            Map<String, TotalCaptureResult> physicalResults = total.getPhysicalCameraTotalResults();
                            result = physicalResults.get(config.physicalId);
                            if (result == null) { finish("failed", "Missing total result for selected physical camera"); return; }
                        } else result = total;
                        event("still_total_result_received");
                        maybeSave();
                    }
                    @Override public void onCaptureFailed(CameraCaptureSession s, CaptureRequest request, CaptureFailure failure) {
                        finish("failed", "still_capture_failed_" + failure.getReason());
                    }
                    @Override public void onCaptureSequenceAborted(CameraCaptureSession s, int sequence) {
                        if (live()) finish("failed", "still_sequence_aborted_" + sequence);
                    }
                }, worker);
                report.put("capture_sequence_id", sequence).put("preview_result_count", previewFrames);
            } catch (Exception error) { finish("failed", "capture: " + error); }
        }

        void onImage(ImageReader source) {
            Image received = null;
            try {
                received = source.acquireNextImage();
                if (received == null) return;
                if (!live() || !submitted || image != null) { received.close(); return; }
                image = received;
                event("still_image_received");
                maybeSave();
            } catch (Exception error) {
                if (received != null && image != received) received.close();
                finish("failed", "image: " + error);
            }
        }

        void maybeSave() {
            if (!live() || image == null || result == null) return;
            try {
                Long timestamp = result.get(CaptureResult.SENSOR_TIMESTAMP);
                report.put("image_timestamp_ns", image.getTimestamp()).put("result_timestamp_ns", timestamp);
                if (timestamp == null || image.getTimestamp() != timestamp.longValue()) {
                    throw new IllegalStateException("Image/result timestamps differ; refusing to create a mismatched DNG or JPEG report");
                }
                if (image.getWidth() != config.width || image.getHeight() != config.height || image.getFormat() != formatValue) {
                    throw new IllegalStateException("Returned image format or dimensions differ from the explicit request");
                }
                report.put("timestamp_match", true).put("image_format", image.getFormat())
                        .put("image_width", image.getWidth()).put("image_height", image.getHeight())
                        .put("exposure_time_ns", result.get(CaptureResult.SENSOR_EXPOSURE_TIME))
                        .put("sensitivity", result.get(CaptureResult.SENSOR_SENSITIVITY))
                        .put("result_pixel_mode", result.get(CaptureResult.SENSOR_PIXEL_MODE))
                        .put("active_physical_id", result.get(CaptureResult.LOGICAL_MULTI_CAMERA_ACTIVE_PHYSICAL_ID));
                // Both pieces of the single capture are held. Release the camera before
                // potentially slow encoding, while retaining the acquired Image and reader.
                event("camera_closed_before_file_processing");
                closeCamera();
                if (!live()) { finish("cancelled", "Cancelled before file write"); return; }
                artifact = new File(directory, formatValue == ImageFormat.RAW_SENSOR ? "capture.dng" : "capture.jpg");
                artifactStage = "writing";
                try (FileOutputStream output = new FileOutputStream(artifact)) {
                    if (formatValue == ImageFormat.RAW_SENSOR) {
                        try (DngCreator creator = new DngCreator(characteristics, result)) {
                            creator.writeImage(output, image);
                        }
                    } else {
                        ByteBuffer bytes = image.getPlanes()[0].getBuffer();
                        byte[] buffer = new byte[64 * 1024];
                        while (bytes.hasRemaining()) {
                            if (!live()) throw new java.util.concurrent.CancellationException("Cancelled during JPEG write");
                            int count = Math.min(bytes.remaining(), buffer.length);
                            bytes.get(buffer, 0, count);
                            output.write(buffer, 0, count);
                        }
                    }
                }
                artifactStage = "written";
                if (!live()) { finish("cancelled", "Cancelled during file write"); return; }
                report.put("file", artifact.getName()).put("file_size_bytes", artifact.length())
                        .put("file_sha256", sha256(artifact));
                if (!live()) { finish("cancelled", "Cancelled during file hashing"); return; }
                artifactStage = "validating";
                if (formatValue != ImageFormat.RAW_SENSOR) verifyJpeg(artifact);
                artifactStage = "validated";
                if (!live()) { finish("cancelled", "Cancelled during image validation"); return; }
                event("file_saved");
                finish("captured", "One image saved with matching total capture result; independent host review is still required");
            } catch (Exception error) { finish(live() ? "failed" : "cancelled", "save: " + error); }
        }

        void verifyJpeg(File file) throws Exception {
            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(file.getAbsolutePath(), bounds);
            report.put("jpeg_width", bounds.outWidth).put("jpeg_height", bounds.outHeight);
            if (bounds.outWidth != config.width || bounds.outHeight != config.height) {
                throw new IllegalStateException("Encoded JPEG dimensions differ from requested dimensions");
            }
            BitmapFactory.Options sample = new BitmapFactory.Options();
            sample.inSampleSize = 1;
            while ((long) bounds.outWidth * bounds.outHeight / sample.inSampleSize / sample.inSampleSize > 4_000_000L) {
                sample.inSampleSize *= 2;
            }
            Bitmap bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), sample);
            if (bitmap == null) throw new IllegalStateException("Encoded JPEG failed decode");
            try {
                report.put("jpeg_decode_sample_size", sample.inSampleSize).put("has_gainmap", bitmap.hasGainmap());
                if (formatValue == ImageFormat.JPEG_R && !bitmap.hasGainmap()) {
                    throw new IllegalStateException("JPEG_R capture returned a JPEG without a decoded gain map");
                }
            } finally { bitmap.recycle(); }
        }

        void closeCamera() {
            if (session != null) { session.close(); session = null; }
            if (device != null) { device.close(); device = null; }
        }

        void finish(String outcome, String detail) {
            // Serialize the final outcome with UI cancellation. A queued cancellation
            // cannot lose to a completed write or a late camera callback on this worker.
            synchronized (this) {
                if (finished) return;
                if (cancellationReason != null || ("captured".equals(outcome)
                        && (!active || !foreground || current != this))) {
                    outcome = "cancelled";
                    detail = cancellationReason == null ? "Activity left foreground before capture finalization"
                            : cancellationReason;
                }
                finished = true;
                active = false;
            }
            worker.removeCallbacks(timeout);
            event("camera_resources_closing");
            closeCamera();
            if (image != null) { image.close(); image = null; }
            if (reader != null) { reader.close(); reader = null; }
            if (preview != null) { preview.release(); preview = null; }
            try {
                if (!"captured".equals(outcome) && artifact != null && artifact.isFile()) {
                    JSONObject partial = new JSONObject().put("file", artifact.getName())
                            .put("size_bytes", artifact.length()).put("stage", artifactStage)
                            .put("admitted", false);
                    try { partial.put("sha256", sha256(artifact)); }
                    catch (Exception error) { partial.put("hash_error", error.toString()); }
                    report.put("partial_artifact", partial);
                }
                report.put("outcome", outcome).put("detail", detail)
                        .put("elapsed_ms", SystemClock.elapsedRealtime() - started);
                writeJson(new File(directory, "report.json"), report);
                show(outcome + ": " + detail + "\nPrivate report: " + directory.getName() + "/report.json\n" + report.toString(2));
            } catch (Exception error) { show("Unable to save test report: " + error); }
            if (current == this) current = null;
            main.post(() -> { inspect.setEnabled(true); capture.setEnabled(true); runPending(); });
            maybeQuit();
        }
    }

    private static boolean contains(int[] values, int target) {
        if (values != null) for (int value : values) if (value == target) return true;
        return false;
    }

    private static boolean contains(long[] values, long target) {
        if (values != null) for (long value : values) if (value == target) return true;
        return false;
    }

    private static boolean contains(Size[] values, Size target) {
        return values != null && Arrays.asList(values).contains(target);
    }

    private static Size selectPreview(Size[] values, Size still) {
        Size best = null;
        double bestScore = Double.MAX_VALUE;
        if (values != null) for (Size size : values) {
            if (size.getWidth() > 1920 || size.getHeight() > 1920
                    || (long) size.getWidth() * size.getHeight() > 1920L * 1080) continue;
            double ratioDelta = Math.abs((double) size.getWidth() / size.getHeight()
                    - (double) still.getWidth() / still.getHeight());
            double score = ratioDelta * 10_000_000 - (long) size.getWidth() * size.getHeight();
            if (score < bestScore) { best = size; bestScore = score; }
        }
        if (best == null) throw new IllegalArgumentException("No public preview size at or below 1920x1080 area");
        return best;
    }

    private static void writeJson(File file, JSONObject report) throws Exception {
        try (FileOutputStream stream = new FileOutputStream(file)) {
            stream.write((report.toString(2) + "\n").getBytes(StandardCharsets.UTF_8));
        }
    }

    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (FileInputStream stream = new FileInputStream(file)) {
            byte[] buffer = new byte[64 * 1024];
            int count;
            while ((count = stream.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        StringBuilder result = new StringBuilder();
        for (byte value : digest.digest()) result.append(String.format("%02x", value & 0xff));
        return result.toString();
    }
}
