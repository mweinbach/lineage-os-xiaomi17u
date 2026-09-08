#include "NezhaCompressedDng.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <vector>
using namespace android::nezha::dng;
static unsigned checks = 0;
#define CHECK(x) do { ++checks; if (!(x)) { std::fprintf(stderr, "Line %d: %s\n", __LINE__, #x); std::abort(); } } while (0)
static std::vector<uint8_t> load(const char* path) {
    std::ifstream f(path, std::ios::binary);
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(f), {});
}
static void put32(std::vector<uint8_t>& data, size_t pos, uint32_t value) {
    for (size_t i = 0; i < 4; ++i) data[pos + i] = (value >> (i * 8)) & 255;
}
int main(int argc, char** argv) {
    CHECK(argc == 4);
    const auto jpeg = load(argv[1]);
    CHECK(jpeg.size() > 20);
    JpegFrame frame;
    CHECK(inspectJpeg(jpeg.data(), jpeg.size(), &frame));
    CHECK(frame.width == 16 && frame.height == 16 && frame.components == 3 &&
            frame.precision == 16 && frame.coding == 0xc3 && frame.size == jpeg.size());
    for (size_t n = 0; n < jpeg.size(); ++n) CHECK(!inspectJpeg(jpeg.data(), n, &frame));
    CHECK(!inspectJpeg(nullptr, jpeg.size(), &frame));
    CHECK(!inspectJpeg(jpeg.data(), jpeg.size(), nullptr));
    auto wrapped = jpeg; wrapped.push_back(0);
    CHECK(inspectJpeg(wrapped.data(), wrapped.size(), &frame) && frame.size == jpeg.size());
    std::vector<uint8_t> metadata(604);
    put32(metadata, 0, 15); put32(metadata, 4, 16); put32(metadata, 8, 16);
    put32(metadata, 12, jpeg.size());
    Layout layout;
    CHECK(!parseLayout(metadata.data(), metadata.size(), jpeg.data(), jpeg.size(), &layout));
    CHECK(layout.linearRaw && !layout.tiled && layout.count == 1 && layout.dataSize == jpeg.size());
    CHECK(parseLayout(metadata.data(), 603, jpeg.data(), jpeg.size(), &layout));
    CHECK(parseLayout(metadata.data(), 605, jpeg.data(), jpeg.size(), &layout));
    CHECK(parseLayout(metadata.data(), metadata.size(), jpeg.data(), jpeg.size() - 1, &layout));
    CHECK(parseLayout(nullptr, metadata.size(), jpeg.data(), jpeg.size(), &layout));
    CHECK(parseLayout(metadata.data(), metadata.size(), nullptr, jpeg.size(), &layout));
    CHECK(parseLayout(metadata.data(), metadata.size(), jpeg.data(), jpeg.size(), nullptr));
    auto bad = metadata;
    for (uint32_t format : {0u, 14u, 16u, UINT32_MAX}) {
        put32(bad, 0, format);
        CHECK(parseLayout(bad.data(), bad.size(), jpeg.data(), jpeg.size(), &layout));
    }
    for (size_t field : {4u, 8u, 12u}) {
        bad = metadata; put32(bad, field, 0);
        CHECK(parseLayout(bad.data(), bad.size(), jpeg.data(), jpeg.size(), &layout));
        put32(bad, field, UINT32_MAX);
        CHECK(parseLayout(bad.data(), bad.size(), jpeg.data(), jpeg.size(), &layout));
    }
    bad = metadata; put32(bad, 16, 2);
    CHECK(parseLayout(bad.data(), bad.size(), jpeg.data(), jpeg.size(), &layout));
    std::vector<uint8_t> tiles;
    for (size_t i = 0; i < 64; ++i) tiles.insert(tiles.end(), jpeg.begin(), jpeg.end());
    put32(metadata, 4, 128); put32(metadata, 8, 128); put32(metadata, 12, tiles.size());
    put32(metadata, 16, 1); put32(metadata, 20, 8); put32(metadata, 24, 8);
    for (size_t i = 0; i < 64; ++i) put32(metadata, 28 + i * 4, jpeg.size());
    CHECK(!parseLayout(metadata.data(), metadata.size(), tiles.data(), tiles.size(), &layout));
    CHECK(layout.tiled && layout.count == 64 && layout.tileWidth == 16 && layout.tileHeight == 16);
    uint32_t previewOffset = 0;
    CHECK(assignOffsets(1234, 51, &layout, &previewOffset));
    for (size_t i = 0; i < 64; ++i) CHECK(layout.offsets[i] == 1234 + i * jpeg.size());
    CHECK(previewOffset == ((1234 + tiles.size() + 1) & ~size_t{1}));
    CHECK(!assignOffsets(UINT32_MAX, 51, &layout, &previewOffset));
    CHECK(!assignOffsets(1234, UINT32_MAX, &layout, &previewOffset));
    for (size_t i = 0; i < 64; ++i) {
        bad = metadata; put32(bad, 28 + 4 * i, 0);
        CHECK(parseLayout(bad.data(), bad.size(), tiles.data(), tiles.size(), &layout));
        put32(bad, 28 + 4 * i, UINT32_MAX);
        CHECK(parseLayout(bad.data(), bad.size(), tiles.data(), tiles.size(), &layout));
        auto broken = tiles; broken[i * jpeg.size() + 1] = 0;
        CHECK(parseLayout(metadata.data(), metadata.size(), broken.data(), broken.size(), &layout));
    }
    for (size_t field : {20u, 24u}) {
        bad = metadata; put32(bad, field, 9);
        CHECK(parseLayout(bad.data(), bad.size(), tiles.data(), tiles.size(), &layout));
    }
    // Bayer is one TIFF sample per pixel, encoded as paired JPEG components.
    // Exercise both single-strip and tile paths, including the measured 4080x3072 grid.
    for (const auto& bayer : {load(argv[2]), load(argv[3])}) {
        CHECK(inspectJpeg(bayer.data(), bayer.size(), &frame));
        CHECK(frame.components == 2 && frame.precision == 16);
        const auto width = frame.width * 2, height = frame.height;
        for (bool tiled : {false, true}) {
            std::vector<uint8_t> m(604), payload;
            put32(m, 0, 32); put32(m, 4, width * (tiled ? 8 : 1));
            put32(m, 8, height * (tiled ? 8 : 1)); put32(m, 16, tiled);
            put32(m, 20, 8); put32(m, 24, 8);
            for (size_t i = 0; i < (tiled ? 64u : 1u); ++i) {
                payload.insert(payload.end(), bayer.begin(), bayer.end());
                put32(m, 28 + 4 * i, bayer.size());
            }
            put32(m, 12, payload.size());
            CHECK(!parseLayout(m.data(), m.size(), payload.data(), payload.size(), &layout));
            CHECK(!layout.linearRaw && layout.tileWidth == width && layout.tileHeight == height);
            CHECK(assignOffsets(1500, 53, &layout, &previewOffset));
            CHECK(layout.offsets[layout.count - 1] + layout.byteCounts[layout.count - 1]
                    <= previewOffset);
            auto mismatch = m; put32(mismatch, 0, 15);
            CHECK(parseLayout(mismatch.data(), mismatch.size(), payload.data(), payload.size(), &layout));
            mismatch = m; put32(mismatch, 4, (width - 1) * (tiled ? 8 : 1));
            CHECK(parseLayout(mismatch.data(), mismatch.size(), payload.data(), payload.size(), &layout));
            mismatch = m; put32(mismatch, 8, (height + 1) * (tiled ? 8 : 1));
            CHECK(parseLayout(mismatch.data(), mismatch.size(), payload.data(), payload.size(), &layout));
            for (size_t i = 0; i < layout.count; ++i) {
                auto incomplete = payload; incomplete[i * bayer.size() + 1] = 0;
                CHECK(parseLayout(m.data(), m.size(), incomplete.data(), incomplete.size(), &layout));
            }
        }
    }
    bad = metadata; put32(bad, 0, 32);
    CHECK(parseLayout(bad.data(), bad.size(), tiles.data(), tiles.size(), &layout));
    // Exercise every marker byte with deterministic mutations under sanitizers.
    for (size_t i = 0; i < jpeg.size(); ++i) {
        for (uint8_t v : {uint8_t{0}, uint8_t{0xff}, uint8_t{0xc3}, uint8_t{0xda}}) {
            auto altered = jpeg; altered[i] = v;
            JpegFrame inspected;
            const bool valid = inspectJpeg(altered.data(), altered.size(), &inspected);
            CHECK(!valid || inspected.size <= altered.size());
        }
    }
    std::printf("%u assertions passed\n", checks);
}
