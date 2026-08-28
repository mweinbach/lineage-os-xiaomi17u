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
    -hardware/interfaces/virtualization/capabilities_service/vts/

# The reviewed Crosvm source closure needs these original AEMU providers.
# Restore only the four audited build files, including their shared metadata;
# the remaining AEMU build files stay outside this recovery profile.
PRODUCT_SOURCE_ROOT_DIRS += \
    hardware/google/aemu/Android.bp \
    hardware/google/aemu/base/Android.bp \
    hardware/google/aemu/host-common/Android.bp \
    hardware/google/aemu/snapshot/Android.bp

# Graph 23 requires the original exported SDK sandbox flags in the framework.
# Keep their parent package metadata/defaults and the complete flags leaf.
PRODUCT_SOURCE_ROOT_DIRS += \
    packages/modules/AdServices/sdksandbox/Android.bp \
    packages/modules/AdServices/sdksandbox/flags/

# Graph 27 requires the original AdServices and SDK sandbox API providers.
# Their shared libraries and generators occupy these sixteen complete files.
# Preserve the original definitions without installing their runtime services;
# the wider AdServices source scope remains excluded.
PRODUCT_SOURCE_ROOT_DIRS += \
    packages/modules/AdServices/Android.bp \
    packages/modules/AdServices/adservices/framework/Android.bp \
    packages/modules/AdServices/adservices/flags/Android.bp \
    packages/modules/AdServices/adservices/linter/Android.bp \
    packages/modules/AdServices/shared/libraries/device-side/Android.bp \
    packages/modules/AdServices/shared/libraries/device-side/proto/Android.bp \
    packages/modules/AdServices/shared/libraries/side-less/Android.bp \
    packages/modules/AdServices/adservices/service-core/Android.bp \
    packages/modules/AdServices/adservices/apk/assets/cobalt/Android.bp \
    packages/modules/AdServices/sdksandbox/framework/Android.bp \
    packages/modules/AdServices/sdksandbox/service/Android.bp \
    packages/modules/AdServices/sdksandbox/service/proto/Android.bp \
    packages/modules/AdServices/sdksandbox/SdkSandbox/Android.bp \
    packages/modules/AdServices/adservices/libraries/cobalt/Android.bp \
    packages/modules/AdServices/adservices/libraries/cobalt/proto/Android.bp \
    packages/modules/AdServices/adservices/service-core/proto/Android.bp

# The graph 31 follow-up source audit found shared framework flags, libraries
# and generators in these five projects. Keep complete original provider files,
# including their original license owners and inseparable app declarations.
# No app is added to PRODUCT_PACKAGES, and dependencies remain strictly checked.
PRODUCT_SOURCE_ROOT_DIRS += \
    -packages/modules/CellBroadcastService/ \
    packages/modules/CellBroadcastService/Android.bp \
    -packages/apps/CellBroadcastReceiver/ \
    packages/apps/CellBroadcastReceiver/apex/permissions/Android.bp \
    -packages/apps/Settings/ \
    packages/apps/Settings/Android.bp \
    packages/apps/Settings/aconfig/Android.bp \
    packages/apps/Settings/protos/Android.bp \
    packages/apps/Settings/src/com/android/settings/biometrics/fingerprint2/lib/Android.bp \
    packages/apps/Settings/src/com/android/settings/fuelgauge/protos/Android.bp \
    -packages/apps/Launcher3/ \
    packages/apps/Launcher3/Android.bp \
    packages/apps/Launcher3/aconfig/Android.bp \
    packages/apps/Launcher3/checks/Android.bp \
    packages/apps/Launcher3/shared/Android.bp \
    -packages/apps/Traceur/ \
    packages/apps/Traceur/Android.bp

# Graph 32 requires the original SDK-sandbox test scenario and its helpers.
# These eight complete provider files retain host/device wrappers, generators,
# metadata and raw source contracts. The wider AdServices test tree stays out.
PRODUCT_SOURCE_ROOT_DIRS += \
    packages/modules/AdServices/adservices/clients/Android.bp \
    packages/modules/AdServices/adservices/tests/test-util/Android.bp \
    packages/modules/AdServices/sdksandbox/tests/testutils/Android.bp \
    packages/modules/AdServices/sdksandbox/tests/testutils/testscenario/testrule/Android.bp \
    packages/modules/AdServices/sdksandbox/tests/testutils/testscenario/textexecutor/Android.bp \
    packages/modules/AdServices/shared/testing-libraries/device-side/Android.bp \
    packages/modules/AdServices/shared/testing-libraries/host-side/Android.bp \
    packages/modules/AdServices/shared/testing-libraries/side-less/Android.bp

# The retained TV Settings API test needs only these two original library files.
# Keep the TV app, unbundled product and Robolectric tests outside this profile.
PRODUCT_SOURCE_ROOT_DIRS += \
    -packages/apps/TvSettings/ \
    packages/apps/TvSettings/SettingsAPI/Android.bp \
    packages/apps/TvSettings/TwoPanelSettingsLib/Android.bp

# Graph 24 needs the original shared STS host utilities. Keep both complete
# provider files and their metadata without selecting sibling test products.
PRODUCT_SOURCE_ROOT_DIRS += \
    platform_testing/libraries/sts-common-util/host-side/Android.bp \
    platform_testing/libraries/sts-common-util/util/Android.bp

# Preserve the retained remote-access test servers' real generated protocol
# library. The surrounding default automotive HAL implementation stays excluded.
PRODUCT_SOURCE_ROOT_DIRS += \
    hardware/interfaces/automotive/remoteaccess/hal/default/proto/Android.bp

# The Car host CTS subtree is a reviewed closed set of automotive tests.
# Keep its car_builtin sibling and the remote-access VTS tests. Those retained
# tests need original Car team metadata; shared API providers are selected below.
PRODUCT_SOURCE_ROOT_DIRS += \
    -cts/hostsidetests/car/ \
    -packages/services/Car/ \
    packages/services/Car/teams/Android.bp

# Retained CTS consumers also require the original Car API/stub generators.
# Select the five audited provider files, without the Car service or tests.
PRODUCT_SOURCE_ROOT_DIRS += \
    packages/services/Car/car-lib/Android.bp \
    packages/services/Car/aconfig/Android.bp \
    packages/services/Car/car-builtin-lib/Android.bp \
    packages/services/Car/libs/car-internal-dep-lib/Android.bp \
    packages/services/Car/prebuilts/Android.bp

# The second graph exposed these specific CTS/VTS and automotive consumers.
# Preserve the rest of CTS and the security HAL interfaces. The original CHRE
# exclusion is removed: graph 22 requires its shared flag declarations, and
# genuine Pigweed/Emboss sources supply the restored subsystem's dependencies.
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
    -hardware/interfaces/security/see/hwcrypto/aidl/vts/functional/

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

# Keep the original NNAPI HAL utilities with the complete NeuralNetworks
# dependency sources. They are shared providers, not optional test stubs.
# The unrelated AIDL functional VTS leaf remains outside this recovery profile.
PRODUCT_SOURCE_ROOT_DIRS += \
    -hardware/interfaces/neuralnetworks/aidl/vts/functional/

# Graph 17 reached the standalone NNAPI CTS test. This reviewed leaf contains
# four tests and their one JNI test library, with no outside module consumers.
# Omit that test family only; preserve all NNAPI interfaces and other CTS tests.
PRODUCT_SOURCE_ROOT_DIRS += \
    -cts/tests/tests/neuralnetworks/

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

# The native source audit found retained Wi-Fi service consumers of this
# original HAL leaf. Do not choose a chipset or enable recovery networking;
# the unchanged upstream defaults apply with no Wi-Fi vendor configuration.
PRODUCT_SOURCE_ROOT_DIRS += \
    frameworks/opt/net/wifi/libwifi_hal/

# Retained SystemUI and Settings consumers also need the original tracker
# library and resources. This exact file has no runner or Robolectric dependency;
# sibling Wi-Fi build files stay excluded and recovery networking stays disabled.
PRODUCT_SOURCE_ROOT_DIRS += \
    frameworks/opt/net/wifi/libs/WifiTrackerLib/Android.bp

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

# The source projection after Graph 13 found retained flag-test consumers.
# Restore only these providers, including their local tests, native aconfig
# declarations and defaults. The bounded dependency check uses existing
# selected providers; runner, collector and rule subtrees remain excluded.
PRODUCT_SOURCE_ROOT_DIRS += \
    platform_testing/libraries/flag-helpers/junit/ \
    platform_testing/libraries/flag-helpers/libflagtest/

# Graph 22 requires the original host test-composer library for Tradefed.
# Keep its own tests and metadata, without selecting the health-test aggregate.
PRODUCT_SOURCE_ROOT_DIRS += \
    platform_testing/libraries/health/composers/host/

# Keep the four remaining Graph 14 Onboarding/SettingsLib test-file cuts.
# The two original Robolectric extension files now have retained consumers and
# are restored; the original patches remain unchanged. Do not exclude their
# parents or production IPC/SDK code.
PRODUCT_SOURCE_ROOT_DIRS += \
    -external/android_onboarding/java/com/android/onboarding/contracts/testing/Android.bp \
    -external/android_onboarding/java/com/android/onboarding/testing/Android.bp \
    -frameworks/base/packages/SettingsLib/tests/robotests/Android.bp \
    -frameworks/base/packages/SettingsLib/tests/robotests/fragment/Android.bp

# Graph 31 requires the original shared collectors, Flicker and app helpers.
# Their complete provider closure spans these fifty existing Blueprint files;
# WifiTrackerLib above completes the audited fifty-one-file helper cohort.
# Keep original libraries, tests, package metadata and type registration intact.
PRODUCT_SOURCE_ROOT_DIRS += \
    platform_testing/libraries/app-helpers/core/Android.bp \
    platform_testing/libraries/app-helpers/handheld/Android.bp \
    platform_testing/libraries/app-helpers/handheld/business-card-app-helper/Android.bp \
    platform_testing/libraries/app-helpers/handheld/performance-launch-app-helper/Android.bp \
    platform_testing/libraries/app-helpers/interfaces/Android.bp \
    platform_testing/libraries/app-helpers/spectatio/spectatio-util/Android.bp \
    platform_testing/libraries/collectors-helper/adservices/Android.bp \
    platform_testing/libraries/collectors-helper/app/Android.bp \
    platform_testing/libraries/collectors-helper/generic/Android.bp \
    platform_testing/libraries/collectors-helper/jank/Android.bp \
    platform_testing/libraries/collectors-helper/lyric/Android.bp \
    platform_testing/libraries/collectors-helper/memory/Android.bp \
    platform_testing/libraries/collectors-helper/perfetto/Android.bp \
    platform_testing/libraries/collectors-helper/power/Android.bp \
    platform_testing/libraries/collectors-helper/simpleperf/Android.bp \
    platform_testing/libraries/collectors-helper/statsd/Android.bp \
    platform_testing/libraries/collectors-helper/system/Android.bp \
    platform_testing/libraries/collectors-helper/utilities/Android.bp \
    platform_testing/libraries/device-collectors/src/main/Android.bp \
    platform_testing/libraries/device-collectors/src/main/platform-collectors/Android.bp \
    platform_testing/libraries/flicker/Android.bp \
    platform_testing/libraries/flicker/appHelpers/Android.bp \
    platform_testing/libraries/flicker/collector/Android.bp \
    platform_testing/libraries/flicker/utils/Android.bp \
    platform_testing/libraries/health/composers/platform/Android.bp \
    platform_testing/libraries/health/options/Android.bp \
    platform_testing/libraries/health/rules/Android.bp \
    platform_testing/libraries/health/runners/microbenchmark/Android.bp \
    platform_testing/libraries/health/utils/Android.bp \
    platform_testing/libraries/launcher-helper/Android.bp \
    platform_testing/libraries/metrics-helper/Android.bp \
    platform_testing/libraries/motion/Android.bp \
    platform_testing/libraries/motion/compose/Android.bp \
    platform_testing/libraries/motion/compose/values/Android.bp \
    platform_testing/libraries/notes-role-test-helper/Android.bp \
    platform_testing/libraries/runner/Android.bp \
    platform_testing/libraries/screenshot/Android.bp \
    platform_testing/libraries/screenshot/utils/compose/Android.bp \
    platform_testing/libraries/sts-common-util/device-side/Android.bp \
    platform_testing/libraries/system-helpers/activity-helper/Android.bp \
    platform_testing/libraries/system-helpers/commands-helper/Android.bp \
    platform_testing/libraries/system-helpers/device-helper/Android.bp \
    platform_testing/libraries/system-helpers/package-helper/Android.bp \
    platform_testing/libraries/system-helpers/sysui-helper/Android.bp \
    platform_testing/libraries/system-helpers/user-helper/Android.bp \
    platform_testing/libraries/uiautomator-helpers/Android.bp \
    platform_testing/libraries/uinput-device-test-helper/Android.bp \
    platform_testing/scripts/perf-setup/Android.bp \
    platform_testing/tests/health/scenarios/Android.bp \
    platform_testing/utils/dpad/Android.bp

# The shared runner needs the real Robolectric library chain. Its two original
# extension files are no longer excluded; restore their real XML listener too.
# The separately reviewed typed test gates leave shared providers selected.
PRODUCT_SOURCE_ROOT_DIRS += \
    platform_testing/libraries/junitxml/Android.bp

# Only these two closed tracing-test declarations have no outside consumers.
# Preserve all other SystemUI files, including the mixed animation library file.
PRODUCT_SOURCE_ROOT_DIRS += \
    -frameworks/libs/systemui/tracinglib/robolectric/Android.bp

# A separate source projection found KeyMint's real libhwtrust_cxx dependency.
# Keep the original hwtrust libraries, CXX bridge, binaries, tests and metadata.
# The rest of tools/security is outside this product; none of those excluded
# modules is a registered service fuzzer. Security validators stay selected.
PRODUCT_SOURCE_ROOT_DIRS += \
    -tools/security/ \
    tools/security/remote_provisioning/hwtrust/

# Do not inherit vendor/twrp/config/common.mk: it adds a rescue-disable
# property, a broad package bundle, and an unrelated recovery installer key.
PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING := true
PRODUCT_SYSTEM_DEFAULT_PROPERTIES += \
    ro.secure=1 \
    ro.adb.secure=1

PRODUCT_COPY_FILES += \
    $(NEZHA_TWRP_DEVICE_PATH)/recovery/root/init.recovery.qcom.rc:recovery/root/init.recovery.qcom.rc
