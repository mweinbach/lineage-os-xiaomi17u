// SPDX-License-Identifier: Apache-2.0
package org.evolution.nezha.dolby;

import android.media.audiofx.AudioEffect;
import java.util.UUID;

/** UI-owned session. No automatic writes, persistence, services or vendor file changes. */
final class DolbyController implements AutoCloseable {
    private static final UUID TYPE = UUID.fromString("ec7178ec-e5e1-4432-a3f4-4657e6795210");
    private static final UUID IMPLEMENTATION = UUID.fromString("9d4921da-8225-4f29-aefa-39537a04bcaa");
    private AudioEffect effect;

    static final class State {
        final boolean enabled;
        final boolean frameworkEnabled;
        final int profileCount;
        final int currentProfile;

        State(boolean enabled, boolean frameworkEnabled, int profileCount, int currentProfile) {
            this.enabled = enabled;
            this.frameworkEnabled = frameworkEnabled;
            this.profileCount = profileCount;
            this.currentProfile = currentProfile;
        }
    }

    private AudioEffect controlledEffect() {
        if (effect == null) {
            effect = new AudioEffect(TYPE, IMPLEMENTATION, 0, 0);
        }
        if (!effect.hasControl()) {
            throw new IllegalStateException("Vendor Dolby effect exists but this app does not have control");
        }
        return effect;
    }

    private int read(int parameter) {
        byte[] response = DolbyProtocol.query(parameter);
        int count = controlledEffect().getParameter(parameter + DolbyProtocol.SET_KEY, response);
        return DolbyProtocol.decode(response, count);
    }

    State inspect() {
        int enabled = read(DolbyProtocol.ENABLE);
        if (enabled != 0 && enabled != 1) {
            throw new IllegalStateException("Unexpected Dolby enable value: " + enabled);
        }
        int count = read(DolbyProtocol.PROFILE_COUNT);
        int current = read(DolbyProtocol.CURRENT_PROFILE);
        DolbyProtocol.checkProfiles(count, current);
        return new State(enabled == 1, controlledEffect().getEnabled(), count, current);
    }

    State setEnabled(boolean enabled) {
        // Inspect first: reject unavailable effects and malformed state before any mutation.
        inspect();
        write(DolbyProtocol.ENABLE, enabled ? 1 : 0);
        DolbyProtocol.checkStatus("Framework enable", controlledEffect().setEnabled(enabled));
        State state = inspect();
        if (state.enabled != enabled || state.frameworkEnabled != enabled) {
            throw new IllegalStateException("Enable readback did not match the requested state");
        }
        return state;
    }

    State setProfile(int profile) {
        State before = inspect();
        if (profile < 0 || profile >= before.profileCount) {
            throw new IllegalArgumentException("Selected profile is outside the reported range");
        }
        write(DolbyProtocol.CURRENT_PROFILE, profile);
        State state = inspect();
        if (state.currentProfile != profile) {
            throw new IllegalStateException("Profile readback did not match the requested profile");
        }
        return state;
    }

    private void write(int parameter, int value) {
        DolbyProtocol.checkStatus("Parameter write", controlledEffect().setParameter(
                DolbyProtocol.SET_KEY, DolbyProtocol.change(parameter, value)));
    }

    @Override public void close() {
        if (effect != null) {
            AudioEffect previous = effect;
            effect = null;
            previous.release();
        }
    }
}
