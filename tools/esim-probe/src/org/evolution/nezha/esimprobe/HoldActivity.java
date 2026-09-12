package org.evolution.nezha.esimprobe;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Process;
import android.se.omapi.Channel;
import android.se.omapi.Reader;
import android.se.omapi.SEService;
import android.se.omapi.Session;
import android.util.Log;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Explicit, bounded diagnostics; no profile, modem, reset or authentication operations. */
public final class HoldActivity extends Activity {
    private static final String TAG = "NezhaEsimProbe";
    private static final String PERMISSION = "android.permission.SECURE_ELEMENT_PRIVILEGED_OPERATION";
    private static final byte[] ISD = {(byte) 0xa0, 0, 0, 1, 0x51, 0, 0, 0};
    private static final byte[] ISD_R = {(byte) 0xa0, 0, 0, 5, 0x59, 0x10, 0x10,
            (byte) 0xff, (byte) 0xff, (byte) 0xff, (byte) 0xff, (byte) 0x89, 0, 0, 1, 0};
    private static final int MAX_PAGES = 16;
    private static DiagnosticRun current;
    private DiagnosticRun run;
    private TextView status;

    private static String hex(byte[] bytes) {
        StringBuilder result = new StringBuilder();
        for (byte value : bytes) result.append(String.format(Locale.ROOT, "%02X", value & 255));
        return result.toString();
    }

    private void report(DiagnosticRun source, String line) {
        Log.i(TAG, line);
        runOnUiThread(() -> {
            if (status != null && (source == null || run == source)) status.append(line + "\n");
        });
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        status = new TextView(this);
        status.setPadding(32, 48, 32, 32);
        status.setTextIsSelectable(true);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(status);
        setContentView(scroll);
        begin(getIntent());
    }

    @Override public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        begin(intent);
    }

    private void begin(Intent intent) {
        String mode = intent.getStringExtra("mode");
        if (mode == null) mode = intent.getBooleanExtra("hold", false) ? "hold" : "inspect";
        int seconds = intent.getIntExtra("seconds", 90);
        int p2 = intent.getIntExtra("p2", 4);
        String requestedReader = intent.getStringExtra("reader");
        if (!(mode.equals("inspect") || mode.equals("hold") || mode.equals("discovery") || mode.equals("registry"))
                || seconds < 2 || seconds > 90 || (mode.equals("discovery") && p2 != 0 && p2 != 4)) {
            report(null, "ERROR invalid mode, seconds outside 2..90, or discovery P2 outside 0/4");
            return;
        }
        if (intent.hasExtra("reader") && (!(mode.equals("inspect") || mode.equals("discovery"))
                || !("eSE1".equals(requestedReader) || "SIM1".equals(requestedReader)
                || "SIM2".equals(requestedReader)))) {
            report(null, "ERROR reader must be eSE1/SIM1/SIM2 and is accepted only for inspect/discovery");
            return;
        }
        boolean granted = getPackageManager().checkPermission(PERMISSION, getPackageName()) == PackageManager.PERMISSION_GRANTED;
        if (!granted) {
            report(null, "PRIVILEGED_PERMISSION_GRANTED false");
            return;
        }
        DiagnosticRun next;
        synchronized (HoldActivity.class) {
            if (current != null) {
                report(null, "ERROR another diagnostic is still active; wait for DONE or send STOP");
                return;
            }
            next = new DiagnosticRun(mode, seconds, p2, requestedReader);
            current = next;
            run = next;
        }
        status.setText("");
        report(next, "PROCESS package=" + getPackageName() + " uid=" + Process.myUid() + " mode=" + mode);
        report(next, "PRIVILEGED_PERMISSION_GRANTED true");
        report(next, "REQUESTED_READER " + (requestedReader == null ? "default" : requestedReader));
        next.start();
    }

    static void stopCurrent() {
        DiagnosticRun active;
        synchronized (HoldActivity.class) { active = current; }
        if (active != null) active.end("STOP_RECEIVED");
        else Log.i(TAG, "STOP_RECEIVED no active diagnostic");
    }

    private final class DiagnosticRun {
        private final String mode;
        private final int seconds;
        private final int discoveryP2;
        private final String readerName;
        private final AtomicBoolean ending = new AtomicBoolean();
        private final AtomicBoolean finished = new AtomicBoolean();
        private final Handler timers = new Handler(Looper.getMainLooper());
        private final ExecutorService io = Executors.newSingleThreadExecutor(task -> new Thread(task, "ese-diagnostic-io"));
        private volatile boolean connected;
        // These references are read and written only by io, including cleanup.
        private SEService service;
        private Session session;
        private Channel channel;
        private boolean selectionAttempted;
        private int responseBytes;

        DiagnosticRun(String mode, int seconds, int discoveryP2, String requestedReader) {
            this.mode = mode;
            this.seconds = seconds;
            this.discoveryP2 = discoveryP2;
            // Only the original inspect default chooses the first eSE reader.
            // Every explicit choice and every channel operation has an exact target.
            this.readerName = requestedReader != null ? requestedReader
                    : mode.equals("inspect") ? null : "eSE1";
        }

        private void emit(String line) { report(this, line); }

        void start() {
            // Independent of the main thread and I/O executor: bounds binding, presence,
            // SELECT, APDU reads and cleanup, including a blocked Binder transaction.
            Thread watchdog = new Thread(() -> {
                try { Thread.sleep(seconds * 1000L); }
                catch (InterruptedException ignored) { return; }
                synchronized (HoldActivity.class) {
                    // A completed run must never kill a subsequent run that
                    // starts as the previous deadline thread wakes up.
                    if (!finished.get() && current == this) {
                        Log.e(TAG, "WATCHDOG_EXIT diagnostics_incomplete=true");
                        Process.killProcess(Process.myPid());
                    }
                }
            }, "ese-diagnostic-deadline");
            watchdog.setDaemon(true);
            watchdog.start();
            timers.postDelayed(() -> end("DEADLINE_REACHED diagnostics_incomplete=true"), seconds * 1000L - 1000L);
            timers.postDelayed(() -> { if (!connected) end("BIND_TIMEOUT"); }, 15000L);
            io.execute(() -> {
                if (ending.get()) return;
                try {
                    service = new SEService(getApplicationContext(), io, this::onConnected);
                } catch (Exception failure) {
                    emit("ERROR bind exception=" + failure.getClass().getSimpleName());
                    end("BIND_FAILED");
                }
            });
        }

        private void reportBytes(String label, byte[] bytes, boolean statusWord) throws Exception {
            emit(label + " length=" + (bytes == null ? -1 : bytes.length) + " sha256="
                    + (bytes == null ? "null" : hex(MessageDigest.getInstance("SHA-256").digest(bytes))));
            if (statusWord && bytes != null && bytes.length >= 2) emit(label + " sw=" + hex(Arrays.copyOfRange(bytes, bytes.length - 2, bytes.length)));
        }

        private void onConnected() {
            if (ending.get() || connected) return;
            connected = true;
            try {
                Reader[] readers = service.getReaders();
                if (ending.get()) return;
                String[] names = new String[readers.length];
                Reader selected = null;
                for (int i = 0; i < readers.length; i++) {
                    names[i] = readers[i].getName();
                    boolean suitable = readerName == null ? names[i].startsWith("eSE")
                            : names[i].equals(readerName);
                    if (selected == null && suitable) selected = readers[i];
                }
                emit("READERS " + Arrays.toString(names));
                if (selected == null) {
                    emit("READER_UNAVAILABLE requested=" + (readerName == null ? "first_eSE" : readerName)
                            + " fallback=false");
                    throw new IllegalStateException("Requested reader is unavailable");
                }
                emit("SELECTED_READER " + selected.getName());
                boolean present = selected.isSecureElementPresent();
                if (ending.get()) return;
                emit("SECURE_ELEMENT_PRESENT " + present);
                if (mode.equals("inspect")) { end("INSPECT_DONE no session or channel opened"); return; }
                if (!present) throw new IllegalStateException("Selected reader reports absent");
                session = selected.openSession();
                if (ending.get()) return;
                emit("SESSION_OPEN");
                if (mode.equals("discovery")) reportBytes("SESSION_ATR", session.getATR(), false);
                if (ending.get()) return;
                byte[] aid = mode.equals("discovery") ? ISD_R : ISD;
                byte p2 = mode.equals("discovery") ? (byte) discoveryP2 : 0;
                emit("SELECT_REQUEST aid=" + hex(aid) + " p2=" + String.format(Locale.ROOT, "%02X", p2));
                selectionAttempted = true;
                channel = session.openLogicalChannel(aid, p2);
                if (ending.get()) return;
                if (channel == null) throw new IllegalStateException("No logical channel");
                emit("CHANNEL_OPEN aid=" + hex(aid) + " max_seconds=" + seconds);
                if (mode.equals("discovery")) {
                    reportBytes("ISD_R_SELECT_RESPONSE", channel.getSelectResponse(), true);
                    end("ISD_R_DISCOVERY_DONE no_extra_apdu=true");
                } else if (mode.equals("registry")) {
                    if (!registry() && !ending.get()) directory();
                    end("REGISTRY_DIAGNOSTIC_DONE");
                } else {
                    emit("READY_FOR_SWITCH no_extra_apdu=true");
                }
            } catch (Exception failure) {
                emit("ERROR exception=" + failure.getClass().getSimpleName() + " diagnostics_incomplete=true");
                if (mode.equals("discovery")) emit((selectionAttempted
                        ? "ISD_R_SELECTION_FAILED" : "ISD_R_SELECTION_NOT_ATTEMPTED")
                        + " existence_inconclusive=true");
                end("DIAGNOSTIC_FAILED");
            }
        }

        private byte[] readCommand(byte[] command, String label) throws Exception {
            if (ending.get()) throw new IllegalStateException("Diagnostic stopping");
            byte[] result = channel.transmit(command);
            if (ending.get()) throw new IllegalStateException("Diagnostic stopping");
            if (result == null || result.length < 2 || result.length > RegistryParser.MAX_BYTES - responseBytes) {
                throw new IllegalArgumentException("Response missing status or exceeds total byte limit");
            }
            responseBytes += result.length;
            emit(label + " response_length=" + result.length + " sw=" + String.format(Locale.ROOT, "%04X", sw(result)));
            return result;
        }

        private int sw(byte[] result) {
            return ((result[result.length - 2] & 255) << 8) | (result[result.length - 1] & 255);
        }

        private void entries(byte[] body, boolean directory) {
            List<RegistryParser.Entry> entries = RegistryParser.parse(body, directory);
            for (RegistryParser.Entry entry : entries) {
                emit("ENTRY source=" + (directory ? "directory" : "registry") + " aid=" + hex(entry.aid)
                        + " lifecycle=" + (entry.lifecycle == null ? "unavailable" : hex(entry.lifecycle)));
            }
            emit((directory ? "DIRECTORY" : "REGISTRY") + "_COMPLETE entries=" + entries.size()
                    + " scope=selected_security_domain absence_is_not_card_wide_proof=true");
        }

        private boolean registry() throws Exception {
            ByteArrayOutputStream body = new ByteArrayOutputStream();
            for (int page = 0; page < MAX_PAGES; page++) {
                byte[] command = {(byte) 0x80, (byte) 0xf2, 0x40, (byte) (page == 0 ? 2 : 3), 2, 0x4f, 0, 0};
                byte[] result = readCommand(command, "GET_STATUS page=" + (page + 1));
                int status = sw(result);
                if (status != 0x9000 && status != 0x6310) {
                    emit("REGISTRY_INCOMPLETE unsupported_or_denied=true no_authentication_attempted=true");
                    return false;
                }
                body.write(result, 0, result.length - 2);
                if (status == 0x9000) {
                    entries(body.toByteArray(), false);
                    return true;
                }
            }
            emit("REGISTRY_INCOMPLETE page_limit=" + MAX_PAGES);
            return false;
        }

        private void directory() throws Exception {
            // GP 2.3.1 sections 11.3.2.2 and 11.3.3.1.3 require tag-list data 5C00.
            byte[] command = {(byte) 0x80, (byte) 0xca, 0x2f, 0, 2, 0x5c, 0, 0};
            byte[] result = readCommand(command, "GET_DATA_2F00");
            if (sw(result) != 0x9000 || result.length == 2) {
                emit("DIRECTORY_INCONCLUSIVE empty_unsupported_or_denied=true");
                return;
            }
            entries(Arrays.copyOf(result, result.length - 2), true);
        }

        void end(String reason) {
            if (!ending.compareAndSet(false, true)) return;
            emit(reason);
            timers.removeCallbacksAndMessages(null);
            // Serialized behind any open/read. Resources created by an in-flight
            // Binder call are assigned before this cleanup can run.
            io.execute(this::cleanup);
        }

        private void cleanup() {
            boolean failed = false;
            if (channel != null) {
                try { channel.close(); emit("CHANNEL_CLOSED"); }
                catch (Exception failure) { emit("CHANNEL_CLOSE_ERROR"); failed = true; }
                channel = null;
            }
            if (session != null) {
                try { session.close(); emit("SESSION_CLOSED"); }
                catch (Exception failure) { emit("SESSION_CLOSE_ERROR"); failed = true; }
                session = null;
            }
            if (service != null) {
                try { service.shutdown(); emit("SERVICE_DISCONNECTED"); }
                catch (Exception failure) { emit("SERVICE_CLOSE_ERROR"); failed = true; }
                service = null;
            }
            if (failed) {
                emit("CLEANUP_INCOMPLETE_PROCESS_EXIT");
                Process.killProcess(Process.myPid());
                return;
            }
            synchronized (HoldActivity.class) {
                finished.set(true);
                if (current == this) current = null;
            }
            io.shutdown();
            emit("DONE");
        }
    }

    @Override public void onDestroy() {
        if (run != null) run.end("ACTIVITY_DESTROYED");
        super.onDestroy();
    }
}
