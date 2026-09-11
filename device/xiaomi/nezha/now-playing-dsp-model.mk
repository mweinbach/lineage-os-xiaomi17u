# SPDX-License-Identifier: Apache-2.0
# Install the Now Playing DSP music-detector model so the Pixel Android System
# Intelligence build can enable ambient music recognition on this Snapdragon unit.
#
# ASI's Now Playing settings switch is enabled only when its AmbientMusicServiceManager
# finds a music-detector sound model on disk: for every non-Tensor device it checks
# /product/etc/firmware/music_detector.sound_model plus music_detector.descriptor
# (then /vendor, then /system). Everything else the feature needs is already present
# on this unit (permissions, flags, the Settings injection, the system music-recognition
# service, and a Qualcomm Sound Trigger HAL module advertising GENERIC_TRIGGER), so the
# missing model pair is the sole blocker; see config/nezha-now-playing-dsp-model.json.
#
# The two files are Google's generic sound model shipped on Snapdragon Pixels (byte
# identical on Pixel 4a 5G, 5 and 5a). They are proprietary and live only in the ignored
# vendor/xiaomi/nezha-nowplaying bundle; this fragment admits them by hash and copies them.
# Whether the SVA 7.0 firmware on this SoC accepts the model is a device result, not a
# build result.
ifneq ($(filter-out 0 1,$(words $(NEZHA_NOW_PLAYING_DSP_MODEL))),)
$(error NEZHA_NOW_PLAYING_DSP_MODEL must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_NOW_PLAYING_DSP_MODEL))),)
$(error NEZHA_NOW_PLAYING_DSP_MODEL must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_NOW_PLAYING_DSP_MODEL)),true)
NEZHA_NOW_PLAYING_BUNDLE ?= vendor/xiaomi/nezha-nowplaying/proprietary/product/etc/firmware
NEZHA_NOW_PLAYING_CONTRACT ?= $(NEZHA_DEVICE_PATH)/now-playing-dsp-model/contract.json
_nezha_now_playing_check := $(shell python3 $(NEZHA_DEVICE_PATH)/now-playing-dsp-model/verify.py --bundle $(NEZHA_NOW_PLAYING_BUNDLE) --contract $(NEZHA_NOW_PLAYING_CONTRACT) 2>&1)
ifneq ($(_nezha_now_playing_check),verified-now-playing-dsp-model)
$(error Now Playing DSP model admission failed: $(_nezha_now_playing_check))
endif
ifneq ($(filter %:$(TARGET_COPY_OUT_PRODUCT)/etc/firmware/music_detector.sound_model,$(PRODUCT_COPY_FILES)),)
$(error Another input already owns the Now Playing sound model destination)
endif
ifneq ($(filter %:$(TARGET_COPY_OUT_PRODUCT)/etc/firmware/music_detector.descriptor,$(PRODUCT_COPY_FILES)),)
$(error Another input already owns the Now Playing descriptor destination)
endif
PRODUCT_COPY_FILES += \
    $(NEZHA_NOW_PLAYING_BUNDLE)/music_detector.sound_model:$(TARGET_COPY_OUT_PRODUCT)/etc/firmware/music_detector.sound_model \
    $(NEZHA_NOW_PLAYING_BUNDLE)/music_detector.descriptor:$(TARGET_COPY_OUT_PRODUCT)/etc/firmware/music_detector.descriptor
endif
