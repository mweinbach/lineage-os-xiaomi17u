/*
 * Copyright 2026 The Android Open Source Project
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software distributed
 * under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
 * CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace android::nezha::dng {

struct JpegFrame {
    uint32_t width = 0;
    uint32_t height = 0;
    uint8_t precision = 0;
    uint8_t components = 0;
    uint8_t coding = 0;
    size_t size = 0;
};

// Inspect marker boundaries, including escaped entropy bytes, without decoding
// or reading past the supplied buffer. The first image may have trailing data
// (for example an Ultra HDR preview's gain map).
inline bool inspectJpeg(const uint8_t* data, size_t size, JpegFrame* result) {
    if (!data || !result || size < 4 || data[0] != 0xff || data[1] != 0xd8) return false;
    JpegFrame frame;
    bool entropy = false;
    bool scan = false;
    size_t p = 2;
    while (p < size) {
        if (entropy) {
            while (p < size && data[p] != 0xff) ++p;
        }
        if (p >= size || data[p++] != 0xff) return false;
        while (p < size && data[p] == 0xff) ++p;
        if (p == size) return false;
        const uint8_t marker = data[p++];
        if (entropy && (marker == 0 || (marker >= 0xd0 && marker <= 0xd7))) continue;
        if (marker == 0xd9) {
            if (!scan || !frame.width || !frame.height) return false;
            frame.size = p;
            *result = frame;
            return true;
        }
        entropy = false;
        if (marker == 0 || marker == 0xd8 || (marker >= 0xd0 && marker <= 0xd7)) return false;
        if (marker == 1) continue;
        if (size - p < 2) return false;
        const size_t length = (static_cast<size_t>(data[p]) << 8) | data[p + 1];
        if (length < 2 || length > size - p) return false;
        if (marker >= 0xc0 && marker <= 0xcf && marker != 0xc4 && marker != 0xc8 && marker != 0xcc) {
            if (frame.width || length < 8) return false;
            frame.precision = data[p + 2];
            frame.height = (static_cast<uint32_t>(data[p + 3]) << 8) | data[p + 4];
            frame.width = (static_cast<uint32_t>(data[p + 5]) << 8) | data[p + 6];
            frame.components = data[p + 7];
            frame.coding = marker;
            if (!frame.width || !frame.height || !frame.components ||
                    length != 8u + 3u * frame.components) return false;
        }
        if (marker == 0xda) {
            if (!frame.width || length < 6 || !data[p + 2] ||
                    data[p + 2] > frame.components || length != 6u + 2u * data[p + 2]) return false;
            scan = true;
            entropy = true;
        }
        p += length;
    }
    return false;
}

struct Layout {
    static constexpr size_t kMetadataBytes = 604;
    static constexpr size_t kMaxTiles = 64;
    uint32_t width = 0;
    uint32_t height = 0;
    uint32_t dataSize = 0;
    uint32_t tileWidth = 0;
    uint32_t tileHeight = 0;
    uint32_t count = 0;
    bool tiled = false;
    std::array<uint32_t, kMaxTiles> byteCounts{};
    std::array<uint32_t, kMaxTiles> offsets{};
};

inline uint32_t read32(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
            (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

// Factory com.xiaomi.dng.compressedParameters: 7 little-endian uint32 fields
// followed by the tile byte counts. Format 15 is interleaved 16-bit LinearRaw.
// Only this measured factory layout is admitted; ordinary RAW uses AOSP's path.
inline const char* parseLayout(const uint8_t* metadata, size_t metadataSize,
        const uint8_t* data, size_t capacity, Layout* result) {
    if (!metadata || metadataSize != Layout::kMetadataBytes || !data || !result) {
        return "Missing or invalid compressed DNG metadata/buffer";
    }
    if (read32(metadata) != 15) return "Unsupported compressed DNG format (expected LinearRaw 15)";
    Layout layout;
    layout.width = read32(metadata + 4);
    layout.height = read32(metadata + 8);
    layout.dataSize = read32(metadata + 12);
    const uint32_t multiThread = read32(metadata + 16);
    if (!layout.width || !layout.height || layout.width > 65535 || layout.height > 65535 ||
            !layout.dataSize || layout.dataSize > capacity || multiThread > 1) {
        return "Invalid compressed DNG dimensions, size or compression mode";
    }
    layout.tiled = multiThread != 0;
    layout.tileWidth = layout.width;
    layout.tileHeight = layout.height;
    layout.count = 1;
    layout.byteCounts[0] = layout.dataSize;
    if (layout.tiled) {
        if (read32(metadata + 20) != 8 || read32(metadata + 24) != 8 ||
                layout.width < 8 || layout.height < 8) return "Unsupported compressed DNG tile grid";
        layout.tileWidth = (layout.width + 7) / 8;
        layout.tileHeight = (layout.height + 7) / 8;
        if ((layout.width + layout.tileWidth - 1) / layout.tileWidth != 8 ||
                (layout.height + layout.tileHeight - 1) / layout.tileHeight != 8) {
            return "Inconsistent compressed DNG tile dimensions";
        }
        layout.count = Layout::kMaxTiles;
        for (size_t i = 0; i < layout.count; ++i) layout.byteCounts[i] = read32(metadata + 28 + 4 * i);
    }
    size_t offset = 0;
    for (size_t i = 0; i < layout.count; ++i) {
        const size_t count = layout.byteCounts[i];
        if (!count || count > layout.dataSize - offset) return "Compressed DNG tile exceeds image data";
        JpegFrame frame;
        if (!inspectJpeg(data + offset, count, &frame) || frame.coding != 0xc3 ||
                frame.precision != 16 || frame.components != 3 ||
                frame.width != layout.tileWidth || frame.height != layout.tileHeight ||
                frame.size != count) return "Invalid lossless JPEG tile in compressed DNG";
        offset += count;
    }
    if (offset != layout.dataSize) return "Compressed DNG tile sizes do not sum to image size";
    *result = layout;
    return nullptr;
}

// Compute TIFF LONG offsets after every metadata entry has been added. Keep the
// preview word aligned without changing any of the encoded lossless image data.
inline bool assignOffsets(uint32_t headerSize, uint32_t previewSize, Layout* layout,
        uint32_t* previewOffset) {
    if (!layout || !previewOffset || !layout->count || layout->count > Layout::kMaxTiles) return false;
    uint64_t offset = headerSize;
    for (size_t i = 0; i < layout->count; ++i) {
        if (offset > std::numeric_limits<uint32_t>::max()) return false;
        layout->offsets[i] = static_cast<uint32_t>(offset);
        offset += layout->byteCounts[i];
    }
    offset = (offset + 1) & ~uint64_t{1};
    if (offset + previewSize > std::numeric_limits<uint32_t>::max()) return false;
    *previewOffset = static_cast<uint32_t>(offset);
    return true;
}

} // namespace android::nezha::dng
