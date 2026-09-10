// SPDX-License-Identifier: Apache-2.0
// Compile-only declarations. The unchanged factory JAR provides the runtime
// class, which loads the encrypted configuration files through its own JNI.
package com.miui.cameraopt.configs;

import org.json.JSONObject;

import java.util.List;

public class JsonDisptcher {
    public interface DataCallback {
        void onDataCallback(JSONObject section);

        void dumpConfigs();
    }

    public JsonDisptcher() {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }

    public static JsonDisptcher getInstance() {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }

    public void loadJson() {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }

    public void registerDataCallback(String key, DataCallback callback) {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }

    public void registerDataCallback(List<String> keys, DataCallback callback) {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }

    public boolean updateCloudData(double version, JSONObject data) {
        throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
    }
}
