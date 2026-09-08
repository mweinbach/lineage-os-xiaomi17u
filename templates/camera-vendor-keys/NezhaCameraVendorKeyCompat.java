/*
 * Copyright (C) 2026 The Android Open Source Project
 * SPDX-License-Identifier: Apache-2.0
 */
package android.hardware.camera2.impl;

import android.app.ActivityThread;
import android.content.res.Resources;
import android.hardware.camera2.CaptureRequest;
import android.os.Build;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Preserves the factory Camera's registered-vendor-key discovery on Nezha.
 *
 * The unmodified Camera APK uses getAllVendorKeys on HyperOS. On AOSP it instead
 * consults getAvailableCaptureRequestKeys, but the retained HAL omits controls
 * such as xiaomi.snapshot.imageName from its advertised request-key list. This
 * opt-in supplies the same registered key catalog only to that Camera process.
 * It does not add native tags, change metadata values, authorize camera access,
 * or establish that every catalog entry works in every sensor/mode combination.
 *
 * @hide
 */
public final class NezhaCameraVendorKeyCompat {
    private NezhaCameraVendorKeyCompat() {}

    @SuppressWarnings("unchecked")
    public static List<CaptureRequest.Key<?>> appendRegisteredKeys(
            List<CaptureRequest.Key<?>> advertised, CameraMetadataNative metadata) {
        if (!"nezha".equals(Build.DEVICE)
                || !"com.android.camera".equals(ActivityThread.currentPackageName())
                || !Resources.getSystem().getBoolean(
                        com.android.internal.R.bool.config_nezhaCameraVendorKeys)) {
            return advertised;
        }

        Class<CaptureRequest.Key<?>> keyClass =
                (Class<CaptureRequest.Key<?>>) (Class<?>) CaptureRequest.Key.class;
        ArrayList<CaptureRequest.Key<?>> registered = metadata.getAllVendorKeys(keyClass);
        if (registered == null || registered.isEmpty()) {
            return advertised;
        }

        Set<String> identities = new HashSet<>();
        for (CaptureRequest.Key<?> key : advertised) {
            identities.add(identity(key));
        }
        ArrayList<CaptureRequest.Key<?>> result = new ArrayList<>(advertised);
        for (CaptureRequest.Key<?> key : registered) {
            if (identities.add(identity(key))) {
                result.add(key);
            }
        }
        return result.size() == advertised.size()
                ? advertised : Collections.unmodifiableList(result);
    }

    private static String identity(CaptureRequest.Key<?> key) {
        return key.getVendorId() + ":" + key.getName();
    }
}
