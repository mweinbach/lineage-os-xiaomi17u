// SPDX-License-Identifier: Apache-2.0
// Compile-only declarations. Never install or statically link this class.
package com.miui.cameraopt.verify;

public final class Verifier {
    private Verifier() {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }

    public static Verifier getInstance() {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }

    public boolean getVerifyResult() {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }

    public void onBootCompleted() {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }
}
