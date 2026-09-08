/*
 * Copyright (C) 2026 The LineageOS Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#pragma once

#include <cstdint>
#include <string>

namespace android {

class CameraMetadata;

namespace camera3 {
struct camera_stream_configuration;
}

namespace nezha {

// Compiled only for the explicitly selected Nezha ARM64 camera integration.
// The proprietary object remains opaque and is allocated by its own library.
class CameraSessionHook final {
public:
    static void registerClient(const std::string& packageName, int api,
            const std::string& cameraId);
    static void initializeDeviceInfo(CameraMetadata& metadata, const std::string& cameraId);
    static bool isMockCamera(const std::string& cameraId);
    static void getCustomBestSize(const CameraMetadata& metadata, int width, int height,
            int format, const std::string& cameraId, int& bestWidth, int& bestHeight);
    static void raiseDimensionsforCustomImageQuality(const CameraMetadata& metadata,
            int width, int height, int format, const std::string& cameraId,
            int& bestWidth, int& bestHeight);
    static void updateSessionParams(CameraMetadata& metadata, const std::string& cameraId);
    static void createCustomDefaultRequest(CameraMetadata& metadata, const std::string& cameraId);
    static void executeSceneIdentify(CameraMetadata& metadata,
            camera3::camera_stream_configuration* configuration, const std::string& cameraId);
    static void detachSceneIdentify(CameraMetadata& metadata);
    static void notifyRequestSubmit(const CameraMetadata& metadata, const std::string& cameraId,
            int uid, int pid, int requestId, bool streaming, const std::string& packageName);
    static void notifyCancelRequest(const std::string& cameraId, int uid, int pid,
            const std::string& packageName, int requestId, int64_t lastFrameNumber);

private:
    CameraSessionHook() = delete;
};

} // namespace nezha
} // namespace android
