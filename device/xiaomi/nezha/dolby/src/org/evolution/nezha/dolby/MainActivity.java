// SPDX-License-Identifier: Apache-2.0
package org.evolution.nezha.dolby;

import android.app.Activity;
import android.graphics.Insets;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;

/** Minimal manual test UI; all vendor access starts in an explicit click/change handler. */
public final class MainActivity extends Activity {
    private final DolbyController controller = new DolbyController();
    private TextView status;
    private Switch enabled;
    private Spinner profiles;
    private Button apply;
    private boolean rendering;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ScrollView scroll = new ScrollView(this);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        int padding = Math.round(20 * getResources().getDisplayMetrics().density);
        content.setPadding(padding, padding, padding, padding);
        scroll.setOnApplyWindowInsetsListener((view, windowInsets) -> {
            Insets bars = windowInsets.getInsets(
                    WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            content.setPadding(padding + bars.left, padding + bars.top,
                    padding + bars.right, padding + bars.bottom);
            return windowInsets;
        });
        scroll.addView(content);
        addText(content, R.string.app_name).setTextSize(24);
        addText(content, R.string.warning);
        Button inspect = new Button(this);
        inspect.setText(R.string.inspect);
        content.addView(inspect);
        status = addText(content, R.string.disconnected);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        enabled = new Switch(this);
        enabled.setText(R.string.enable);
        enabled.setSaveEnabled(false);
        content.addView(enabled);
        TextView label = addText(content, R.string.profile_label);
        profiles = new Spinner(this);
        profiles.setId(View.generateViewId());
        profiles.setSaveEnabled(false);
        label.setLabelFor(profiles.getId());
        content.addView(profiles);
        apply = new Button(this);
        apply.setText(R.string.apply_profile);
        content.addView(apply);
        addText(content, R.string.profile_warning);
        setControls(false);
        inspect.setOnClickListener(view -> perform(() -> controller.inspect()));
        enabled.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) perform(() -> controller.setEnabled(checked));
        });
        apply.setOnClickListener(view -> {
            int selected = profiles.getSelectedItemPosition();
            if (selected < 0) {
                status.setText(R.string.no_selection);
                return;
            }
            perform(() -> controller.setProfile(selected));
        });
        setContentView(scroll);
    }

    private TextView addText(LinearLayout content, int resource) {
        TextView text = new TextView(this);
        text.setText(resource);
        text.setPadding(0, 12, 0, 12);
        content.addView(text);
        return text;
    }

    private interface Action {
        DolbyController.State run();
    }

    private void perform(Action action) {
        setControls(false);
        try {
            show(action.run());
        } catch (RuntimeException failure) {
            disconnect();
            status.setText(getString(R.string.error,
                    failure.getClass().getSimpleName() + ": " + failure.getMessage()));
            // Keep controls disabled until another explicit inspection succeeds.
        }
    }

    private String profileLabel(int id) {
        String name = DolbyProtocol.knownProfileName(id);
        return name == null ? getString(R.string.profile_unknown, id)
                : getString(R.string.profile_named, id, name);
    }

    private void show(DolbyController.State state) {
        rendering = true;
        try {
            enabled.setChecked(state.enabled);
            String[] labels = new String[state.profileCount];
            for (int id = 0; id < labels.length; id++) labels[id] = profileLabel(id);
            ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                    android.R.layout.simple_spinner_item, labels);
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
            profiles.setAdapter(adapter);
            profiles.setSelection(state.currentProfile);
            status.setText(getString(R.string.state,
                    getString(state.enabled ? R.string.on : R.string.off),
                    getString(state.frameworkEnabled ? R.string.on : R.string.off),
                    profileLabel(state.currentProfile), state.profileCount));
            setControls(true);
        } finally {
            rendering = false;
        }
    }

    private void setControls(boolean available) {
        enabled.setEnabled(available);
        profiles.setEnabled(available);
        apply.setEnabled(available);
    }

    @Override protected void onStop() {
        disconnect();
        setControls(false);
        status.setText(R.string.disconnected);
        super.onStop();
    }

    private void disconnect() {
        try {
            controller.close();
        } catch (RuntimeException ignored) {
            // The handle was detached before release; teardown must not crash the activity.
        }
    }
}
