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

#define LOG_TAG "NezhaCameraSession"

#include "NezhaCameraSessionHook.h"

#include <cstddef>
#include <dlfcn.h>

#include <camera/CameraMetadata.h>
#include <camera/VendorTagDescriptor.h>
#include <camera_metadata_hidden.h>
#include <log/log.h>
#include <utils/String16.h>
#include <utils/String8.h>

#include "device3/InFlightRequest.h"

// This is the library's global class name, used only as an opaque pointer.
class CameraImpl;

namespace android::nezha {
namespace {

// Pin the layouts actually read by the measured factory library. In particular,
// camera_stream is the framework type, not the older hardware/camera3.h type.
static_assert(sizeof(void*) == 8, "The factory camera hook requires ARM64 pointers");
static_assert(sizeof(std::string) == 24, "The factory camera hook requires the libc++ string ABI");
static_assert(sizeof(CameraMetadata) == 24, "The factory camera hook requires this metadata ABI");
static_assert(sizeof(String8) == 8, "The factory camera hook requires this String8 ABI");
static_assert(sizeof(long) == sizeof(int64_t), "The factory cancel hook requires a 64-bit long");
static_assert(offsetof(camera3::camera_stream, width) == 4);
static_assert(offsetof(camera3::camera_stream, height) == 8);
static_assert(offsetof(camera3::camera_stream, format) == 12);
static_assert(offsetof(camera3::camera_stream, use_case) == 104);
static_assert(offsetof(camera3::camera_stream_configuration, num_streams) == 0);
static_assert(offsetof(camera3::camera_stream_configuration, streams) == 8);
static_assert(offsetof(camera3::camera_stream_configuration, operation_mode) == 16);

struct Api final {
    using Create = CameraImpl* (*)();
    using HookModuleInit = void (*)(CameraImpl*);
    using SplitClient = void (*)(CameraImpl*, const String16&, std::string&, std::string&);
    using SetActivity = void (*)(CameraImpl*, const std::string&, const String8&);
    using SetPackage = void (*)(CameraImpl*, const String16&, int, const String8&);
    using ParseCustomization = void (*)(CameraImpl*, const String8&);
    using MetadataWithId = void (*)(CameraImpl*, CameraMetadata&, const String8&);
    using IsMockCamera = bool (*)(CameraImpl*, const String8&);
    using CustomSize = void (*)(CameraImpl*, const CameraMetadata&, int, int, int,
            const String8&, int&, int&);
    using ExecuteScene = void (*)(CameraImpl*, CameraMetadata&,
            camera3::camera_stream_configuration*, const String8&);
    using DetachScene = void (*)(CameraImpl*, CameraMetadata&);
    using NotifySubmit = void (*)(CameraImpl*, const CameraMetadata&, const std::string&,
            int, int, int, bool, const std::string&);
    using NotifyCancel = void (*)(CameraImpl*, const std::string&, int, int,
            const std::string&, int, long);

    CameraImpl* object = nullptr;
    SplitClient splitClient = nullptr;
    SetActivity setActivity = nullptr;
    SetPackage setPackage = nullptr;
    ParseCustomization parseCustomization = nullptr;
    MetadataWithId initializeDeviceInfo = nullptr;
    MetadataWithId updateSessionParams = nullptr;
    MetadataWithId createCustomDefaultRequest = nullptr;
    IsMockCamera isMockCamera = nullptr;
    CustomSize getCustomBestSize = nullptr;
    CustomSize raiseDimensionsforCustomImageQuality = nullptr;
    ExecuteScene executeSceneIdentify = nullptr;
    DetachScene detachSceneIdentify = nullptr;
    NotifySubmit notifyRequestSubmit = nullptr;
    NotifyCancel notifyCancelRequest = nullptr;

    static const Api& get() {
        // The loader guard is held only during construction. The object and
        // handle survive until process exit, avoiding destructor/dlclose races.
        static const Api* const api = new Api;
        return *api;
    }

private:
    void* handle = nullptr;

    template <typename Function>
    bool resolve(Function& function, const char* name) {
        dlerror();
        void* symbol = dlsym(handle, name);
        const char* error = dlerror();
        if (error != nullptr || symbol == nullptr) {
            ALOGE("Camera session hook disabled: dlsym %s failed: %s", name,
                    error != nullptr ? error : "null symbol");
            return false;
        }
        function = reinterpret_cast<Function>(symbol);
        return true;
    }

    Api() {
        handle = dlopen("/system_ext/lib64/libcameraimpl.so", RTLD_NOW | RTLD_LOCAL);
        if (handle == nullptr) {
            const char* error = dlerror();
            ALOGE("Camera session hook disabled: dlopen failed: %s",
                    error != nullptr ? error : "unknown linker error");
            return;
        }

        Create create = nullptr;
        HookModuleInit hookModuleInit = nullptr;
        // These exported base methods are also the factory Qcom implementation
        // for this ABI. Resolve everything before creating a usable object.
        if (!resolve(create, "create") ||
                !resolve(hookModuleInit, "_ZN10CameraImpl14hookModuleInitEv") ||
                !resolve(splitClient,
                        "_ZN10CameraImpl30splitClientPackageActivityNameERKN7android8String16E"
                        "RNSt3__112basic_stringIcNS4_11char_traitsIcEENS4_9allocatorIcEEEESB_") ||
                !resolve(setActivity,
                        "_ZN10CameraImpl21setClientActivityNameERKNSt3__112basic_stringIcNS0_"
                        "11char_traitsIcEENS0_9allocatorIcEEEERKN7android7String8E") ||
                !resolve(setPackage,
                        "_ZN10CameraImpl20setClientPackageNameERKN7android8String16EiRKNS0_7String8E") ||
                !resolve(parseCustomization,
                        "_ZN10CameraImpl23parseCustomizedJsonDataERKN7android7String8E") ||
                !resolve(initializeDeviceInfo,
                        "_ZN10CameraImpl20initializeDeviceInfoERN7android14CameraMetadataERKNS0_7String8E") ||
                !resolve(isMockCamera,
                        "_ZN10CameraImpl12isMockCameraERKN7android7String8E") ||
                !resolve(getCustomBestSize,
                        "_ZN10CameraImpl17getCustomBestSizeERKN7android14CameraMetadataEiii"
                        "RKNS0_7String8ERiS7_") ||
                !resolve(raiseDimensionsforCustomImageQuality,
                        "_ZN10CameraImpl36raiseDimensionsforCustomImageQualityERKN7android14"
                        "CameraMetadataEiiiRKNS0_7String8ERiS7_") ||
                !resolve(updateSessionParams,
                        "_ZN10CameraImpl19updateSessionParamsERN7android14CameraMetadataERKNS0_7String8E") ||
                !resolve(createCustomDefaultRequest,
                        "_ZN10CameraImpl26createCustomDefaultRequestERN7android14CameraMetadataERKNS0_7String8E") ||
                !resolve(executeSceneIdentify,
                        "_ZN10CameraImpl20executeSceneIdentifyERN7android14CameraMetadataEPNS0_"
                        "7camera327camera_stream_configurationERKNS0_7String8E") ||
                !resolve(detachSceneIdentify,
                        "_ZN10CameraImpl19detachSceneIdentifyERN7android14CameraMetadataE") ||
                !resolve(notifyRequestSubmit,
                        "_ZN10CameraImpl19notifyRequestSubmitERKN7android14CameraMetadataERKNSt3__1"
                        "12basic_stringIcNS4_11char_traitsIcEENS4_9allocatorIcEEEEiiibSC_") ||
                !resolve(notifyCancelRequest,
                        "_ZN10CameraImpl19notifyCancelRequestERKNSt3__112basic_stringIcNS0_"
                        "11char_traitsIcEENS0_9allocatorIcEEEEiiS8_il")) {
            return;
        }

        CameraImpl* const created = create();
        if (created == nullptr) {
            ALOGE("Camera session hook disabled: factory create returned null");
            return;
        }
        hookModuleInit(created);
        object = created;
        ALOGI("Loaded factory camera session hook");
    }
};

camera_metadata_ro_entry_t findTag(const CameraMetadata& metadata,
        const sp<VendorTagDescriptor>& descriptor, const char* name) {
    camera_metadata_ro_entry_t entry{};
    uint32_t tag = 0;
    if (CameraMetadata::getTagFromName(name, descriptor.get(), &tag) == OK) {
        entry = metadata.find(tag);
    }
    return entry;
}

void logSessionTags(const CameraMetadata& metadata, const std::string& cameraId) {
    sp<VendorTagDescriptor> descriptor = VendorTagDescriptor::getGlobalVendorTagDescriptor();
    if (descriptor == nullptr || descriptor->getTagCount() <= 0) {
        descriptor.clear();
        const sp<VendorTagDescriptorCache> cache =
                VendorTagDescriptorCache::getGlobalVendorTagCache();
        if (cache != nullptr) {
            const camera_metadata_t* raw = metadata.getAndLock();
            const metadata_vendor_id_t vendorId = get_camera_metadata_vendor_id(raw);
            metadata.unlock(raw);
            cache->getVendorTagDescriptor(vendorId, &descriptor);
        }
    }
    if (descriptor == nullptr) {
        ALOGW("Camera %s session tags: vendor descriptor unavailable", cameraId.c_str());
        return;
    }

    const auto usecase = findTag(metadata, descriptor, "com.xiaomi.sessionparams.MiStreamUsecase");
    const auto client = findTag(metadata, descriptor, "com.xiaomi.sessionparams.clientName");
    const auto activity = findTag(metadata, descriptor, "com.xiaomi.sessionparams.activityName");
    if (usecase.count > 0 && usecase.type == TYPE_INT32) {
        ALOGI("Camera %s session tags: MiStreamUsecase count=%zu type=%d value=%d; "
                "clientName count=%zu type=%d; activityName count=%zu type=%d",
                cameraId.c_str(), usecase.count, usecase.type, usecase.data.i32[0],
                client.count, client.type, activity.count, activity.type);
    } else {
        ALOGW("Camera %s session tags: MiStreamUsecase count=%zu type=%d value=unavailable; "
                "clientName count=%zu type=%d; activityName count=%zu type=%d",
                cameraId.c_str(), usecase.count, usecase.type,
                client.count, client.type, activity.count, activity.type);
    }
}

} // namespace

void CameraSessionHook::registerClient(const std::string& packageName, int api,
        const std::string& cameraId) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    const String16 validatedPackage(packageName.c_str());
    const String8 id(cameraId.c_str());
    std::string splitPackage = "none";
    std::string activity = "none";
    hook.splitClient(hook.object, validatedPackage, splitPackage, activity);
    hook.setActivity(hook.object, activity, id);
    // Registration retains the framework's validated package identity.
    hook.setPackage(hook.object, validatedPackage, api, id);
    hook.parseCustomization(hook.object, id);
}

void CameraSessionHook::initializeDeviceInfo(CameraMetadata& metadata, const std::string& cameraId) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.initializeDeviceInfo(hook.object, metadata, String8(cameraId.c_str()));
}

bool CameraSessionHook::isMockCamera(const std::string& cameraId) {
    const Api& hook = Api::get();
    return hook.object != nullptr && hook.isMockCamera(hook.object, String8(cameraId.c_str()));
}

void CameraSessionHook::getCustomBestSize(const CameraMetadata& metadata,
        int width, int height, int format, const std::string& cameraId,
        int& bestWidth, int& bestHeight) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.getCustomBestSize(hook.object, metadata, width, height, format,
            String8(cameraId.c_str()), bestWidth, bestHeight);
}

void CameraSessionHook::raiseDimensionsforCustomImageQuality(const CameraMetadata& metadata,
        int width, int height, int format, const std::string& cameraId,
        int& bestWidth, int& bestHeight) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.raiseDimensionsforCustomImageQuality(hook.object, metadata, width, height, format,
            String8(cameraId.c_str()), bestWidth, bestHeight);
}

void CameraSessionHook::updateSessionParams(CameraMetadata& metadata, const std::string& cameraId) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.updateSessionParams(hook.object, metadata, String8(cameraId.c_str()));
}

void CameraSessionHook::createCustomDefaultRequest(CameraMetadata& metadata,
        const std::string& cameraId) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.createCustomDefaultRequest(hook.object, metadata, String8(cameraId.c_str()));
}

void CameraSessionHook::executeSceneIdentify(CameraMetadata& metadata,
        camera3::camera_stream_configuration* configuration, const std::string& cameraId) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.executeSceneIdentify(hook.object, metadata, configuration, String8(cameraId.c_str()));
    logSessionTags(metadata, cameraId);
}

void CameraSessionHook::detachSceneIdentify(CameraMetadata& metadata) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.detachSceneIdentify(hook.object, metadata);
}

void CameraSessionHook::notifyRequestSubmit(const CameraMetadata& metadata,
        const std::string& cameraId, int uid, int pid, int requestId, bool streaming,
        const std::string& packageName) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.notifyRequestSubmit(hook.object, metadata, cameraId, uid, pid, requestId, streaming,
            packageName);
}

void CameraSessionHook::notifyCancelRequest(const std::string& cameraId, int uid, int pid,
        const std::string& packageName, int requestId, int64_t lastFrameNumber) {
    const Api& hook = Api::get();
    if (hook.object == nullptr) return;
    hook.notifyCancelRequest(hook.object, cameraId, uid, pid, packageName, requestId,
            static_cast<long>(lastFrameNumber));
}

} // namespace android::nezha
