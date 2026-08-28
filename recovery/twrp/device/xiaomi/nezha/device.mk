# SPDX-License-Identifier: Apache-2.0

NEZHA_TWRP_DEVICE_PATH := device/xiaomi/nezha

# TARGET_NO_KERNEL suppresses the implicit recovery image rule. This explicit
# product switch builds the dedicated ramdisk image without a placeholder kernel.
PRODUCT_BUILD_RECOVERY_IMAGE := true
PRODUCT_BUILD_BOOT_IMAGE := false
PRODUCT_BUILD_INIT_BOOT_IMAGE := false
PRODUCT_BUILD_VENDOR_BOOT_IMAGE := false
PRODUCT_BUILD_SYSTEM_IMAGE := false
PRODUCT_BUILD_SYSTEM_EXT_IMAGE := false
PRODUCT_BUILD_PRODUCT_IMAGE := false
PRODUCT_BUILD_VENDOR_IMAGE := false
PRODUCT_BUILD_ODM_IMAGE := false
PRODUCT_BUILD_USERDATA_IMAGE := false
PRODUCT_BUILD_CACHE_IMAGE := false
PRODUCT_BUILD_VBMETA_IMAGE := false

PRODUCT_PACKAGES += recovery

# The minimal manifest retains these consumers without their parent defaults.
# Exclude only subsystems outside this no-network/no-crypto recovery product.
# Blueprint matches literal prefixes: the terminal slash prevents a similarly
# named sibling from being excluded. Unmatched paths stay enabled; dependencies
# on an excluded module remain errors and require a reviewed source restoration.
# Keep recovery, fs_mgr, SELinux, AVB, storage and device assertions in the graph.
PRODUCT_SOURCE_ROOT_DIRS += \
    -hardware/google/aemu/ \
    -packages/modules/AdServices/ \
    -hardware/interfaces/neuralnetworks/utils/ \
    -hardware/interfaces/virtualization/capabilities_service/vts/

# The second graph exposed these specific CTS/VTS, automotive and context-hub
# consumers. Their missing parent defaults are unrelated
# to the first recovery product. CHRE includes a runtime subsystem, not just
# test generators. Preserve the rest of CTS and the security HAL interfaces.
PRODUCT_SOURCE_ROOT_DIRS += \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2019-1988/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-21085/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-40114/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-4863/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43091/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43097/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43767/ \
    -cts/tests/tests/car/ \
    -cts/tests/tests/car_permission_tests/ \
    -hardware/interfaces/automotive/remoteaccess/hal/default/ \
    -hardware/interfaces/security/see/hwcrypto/aidl/vts/functional/ \
    -system/chre/

# Graph 3 proved Connectivity/tests/common also owns shared defaults used by
# retained modules. Keep it included and restore the genuine Android 16 r1
# NetworkStack provider instead of excluding its dependent tests or inventing
# libnetworkstackutilsjni_deps.

# Graph 4 adds only these automotive implementations/tests and Secretkeeper
# VTS support tools. Production security and automotive AIDL definitions stay
# included. None of their defined module names is directly referenced by the
# reviewed recovery/core/ADB/vold or protected validation roots.
PRODUCT_SOURCE_ROOT_DIRS += \
    -hardware/interfaces/automotive/vehicle/vts/ \
    -hardware/interfaces/automotive/audiocontrol/aidl/default/ \
    -hardware/interfaces/automotive/vehicle/aidl/impl/3/ \
    -hardware/interfaces/automotive/vehicle/aidl/impl/current/ \
    -hardware/interfaces/security/secretkeeper/aidl/vts/

# Keep NNAPI's HIDL/AIDL interface definitions. These implementation utilities
# and their AIDL VTS consumer depend on the absent NeuralNetworks runtime and
# its external ML libraries; none is part of the initial recovery product.
PRODUCT_SOURCE_ROOT_DIRS += \
    -hardware/interfaces/neuralnetworks/1.0/utils/ \
    -hardware/interfaces/neuralnetworks/1.1/utils/ \
    -hardware/interfaces/neuralnetworks/1.2/utils/ \
    -hardware/interfaces/neuralnetworks/1.3/utils/ \
    -hardware/interfaces/neuralnetworks/aidl/utils/ \
    -hardware/interfaces/neuralnetworks/aidl/vts/functional/

# Omit only the unrelated scene-transition test module. A directory exclusion
# would also hide tests/utils/Android.bp, whose helper has retained consumers.
PRODUCT_SOURCE_ROOT_DIRS += \
    -frameworks/base/packages/SystemUI/compose/scene/tests/Android.bp

# Graph 5 found vehicle compatibility and property-annotation tests consuming
# the omitted vehicle implementation. This directory defines only those three
# test modules, with no external consumers or shared provider to preserve.
PRODUCT_SOURCE_ROOT_DIRS += \
    -hardware/interfaces/automotive/vehicle/aidl/aidl_test/

# The remaining literal vehicle-header consumer is a single broadcast-radio
# unit test. Preserve the production radio service and its AIDL interface.
PRODUCT_SOURCE_ROOT_DIRS += \
    -hardware/interfaces/broadcastradio/aidl/default/test/

# Restore the actual Tradefed defaults without importing platform_testing's
# unrelated test aggregate. Blueprint's more specific positive prefix admits
# this original provider subtree; its own package uses the global license.
# tools/loganalysis, tools/tradefederation/contrib and test/suite_harness stay
# included. Source synchronization supplies the complete pinned project bytes.
PRODUCT_SOURCE_ROOT_DIRS += \
    -platform_testing/ \
    platform_testing/libraries/tradefed-error-prone/

# Graph 6 requires the genuine wificond fuzzer and its Wi-Fi interface libraries.
# Select this self-contained provider and test-support subtree, not unrelated
# tracker/framework consumers. Its package uses the global Apache license.
PRODUCT_SOURCE_ROOT_DIRS += \
    -frameworks/opt/net/wifi/ \
    frameworks/opt/net/wifi/libwifi_system_iface/

# The restored AVF project supplies its build flags and consumes the original
# Secretkeeper client/communication libraries from microdroid_manager. Keep
# system/secretkeeper included; source selection does not enable TWRP crypto.
# Its retained tests require the original Rust test provider in this subtree.
# Keep its module definitions and metadata unchanged, including its own tests.
PRODUCT_SOURCE_ROOT_DIRS += \
    platform_testing/libraries/rdroidtest/

# Graph 9 reached an SDK-distribution-only lambda-stub consumer. This scope
# contains just five SDK archive/helper modules, with no external module
# consumers in the bounded scan. Actual ADB, fastboot, image and signing tools
# remain selected from their original provider directories.
PRODUCT_SOURCE_ROOT_DIRS += \
    -development/build/

# The pinned media source adds audio NNAPI/TensorFlow tests unrelated to this
# recovery. This one file declares 39 tests, one local test default and six
# test tools, with no external module consumers in the bounded scan. Preserve
# production audio, benchmarks, fuzzers and all other test Blueprint files.
PRODUCT_SOURCE_ROOT_DIRS += \
    -system/media/audio_utils/tests/Android.bp

# Graph 11 proved retained suite-harness and framework-tool consumers need
# these original compatibility/annotation providers. Include their child tests
# and wrappers too; their own packages use the global Apache license. The
# platform_testing root test aggregate remains excluded.
PRODUCT_SOURCE_ROOT_DIRS += \
    platform_testing/libraries/compatibility-common-util/ \
    platform_testing/libraries/annotations/

# Do not inherit vendor/twrp/config/common.mk: it adds a rescue-disable
# property, a broad package bundle, and an unrelated recovery installer key.
PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING := true
PRODUCT_SYSTEM_DEFAULT_PROPERTIES += \
    ro.secure=1 \
    ro.adb.secure=1

PRODUCT_COPY_FILES += \
    $(NEZHA_TWRP_DEVICE_PATH)/recovery/root/init.recovery.qcom.rc:recovery/root/init.recovery.qcom.rc
