# SPDX-License-Identifier: Apache-2.0
# Select the factory camcorder profile table, as the factory system image does
# ("media.settings.xml=/vendor/etc/media_profiles_vendor.xml"). The QTI-patched
# MediaProfiles loader only consults ro.media.xml_variant.codecs when this key
# names a /vendor/etc path; it then loads /vendor/etc/media_profiles_canoe_v2.xml,
# which carries the 4K, 8K, DCI and high-speed profiles. Without the key the
# loader falls back to the generic media_profiles_V1_0.xml, whose highest
# quality is 1080p30, and the Xiaomi camera offers no other video resolution or
# frame rate; see config/nezha-camera-video-profiles.json.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERA_VIDEO_PROFILES))),)
$(error NEZHA_CAMERA_VIDEO_PROFILES must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERA_VIDEO_PROFILES))),)
$(error NEZHA_CAMERA_VIDEO_PROFILES must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERA_VIDEO_PROFILES)),true)
ifneq ($(filter media.settings.xml=%,$(PRODUCT_SYSTEM_PROPERTIES)),)
$(error NEZHA_CAMERA_VIDEO_PROFILES requires exclusive ownership of media.settings.xml)
endif
PRODUCT_SYSTEM_PROPERTIES += \
    media.settings.xml=/vendor/etc/media_profiles_vendor.xml
endif
