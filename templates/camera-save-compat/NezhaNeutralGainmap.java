/*
 * Copyright (C) 2026 The LineageOS Project
 * SPDX-License-Identifier: Apache-2.0
 */
package org.lineageos.aperture.compat;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Narrow interoperability repair for the factory front HDR extension. */
public final class NezhaNeutralGainmap {
    public static final int MAX_BYTES = 64 * 1024 * 1024;
    private static final String XMP = "http://ns.adobe.com/xap/1.0/\0";
    private static final String NAMESPACE =
            "xmlns:hdrgm=\"http://ns.adobe.com/hdr-gain-map/1.0/\"";

    private NezhaNeutralGainmap() {}

    private static final class Image {
        int end;
        final List<int[]> iso = new ArrayList<>();
        final List<int[]> xmp = new ArrayList<>();
    }

    private static boolean startsWith(byte[] bytes, int offset, int end, String value) {
        if (offset < 0 || end - offset < value.length()) return false;
        for (int i = 0; i < value.length(); i++) {
            if ((bytes[offset + i] & 255) != value.charAt(i)) return false;
        }
        return true;
    }

    private static Image inspect(byte[] bytes, int start) {
        if (start < 0 || bytes.length - start < 4 ||
                (bytes[start] & 255) != 255 || (bytes[start + 1] & 255) != 216) return null;
        Image image = new Image();
        boolean entropy = false;
        boolean scanned = false;
        int p = start + 2;
        while (p < bytes.length) {
            if (entropy) while (p < bytes.length && (bytes[p] & 255) != 255) p++;
            if (p == bytes.length || (bytes[p++] & 255) != 255) return null;
            while (p < bytes.length && (bytes[p] & 255) == 255) p++;
            if (p == bytes.length) return null;
            int marker = bytes[p++] & 255;
            if (entropy && (marker == 0 || (marker >= 208 && marker <= 215))) continue;
            if (marker == 217) {
                if (!scanned) return null;
                image.end = p;
                return image;
            }
            entropy = false;
            if (marker == 0 || marker == 216 || (marker >= 208 && marker <= 215)) return null;
            if (marker == 1) continue;
            if (bytes.length - p < 2) return null;
            int length = ((bytes[p] & 255) << 8) | (bytes[p + 1] & 255);
            if (length < 2 || length > bytes.length - p) return null;
            if (marker == 225 && startsWith(bytes, p + 2, p + length, XMP)) {
                image.xmp.add(new int[]{p + 2 + XMP.length(), p + length});
            }
            if (marker == 226 && startsWith(bytes, p + 2, p + length,
                    "urn:iso:std:iso:ts:21496:-1\0")) {
                image.iso.add(new int[]{p + 2 + 28, p + length});
            }
            if (marker == 218) {
                if (length < 6) return null;
                entropy = true;
                scanned = true;
            }
            p += length;
        }
        return null;
    }

    private static int attribute(String xmp, String name, String value) {
        Pattern pattern = Pattern.compile("hdrgm:" + name + "\\s*=\\s*\"([^\"]*)\"");
        Matcher matcher = pattern.matcher(xmp);
        if (!matcher.find() || !matcher.group(1).equals(value)) return -1;
        int offset = matcher.start(1);
        return matcher.find() ? -1 : offset;
    }

    /**
     * Return XMP and optional ISO capacity offsets, or an empty array for other files.
     * XMP capacity is log2: this makes the full-HDR endpoint 2 while all pixel
     * gains remain exactly 1. Offsets, JPEG data, EXIF and MPF sizes stay intact.
     */
    public static int[] capacityBytes(byte[] bytes) {
        if (bytes == null || bytes.length > MAX_BYTES) return new int[0];
        Image primary = inspect(bytes, 0);
        if (primary == null) return new int[0];
        boolean container = false;
        for (int[] range : primary.xmp) {
            String text = new String(bytes, range[0], range[1] - range[0], StandardCharsets.ISO_8859_1);
            if (text.contains(NAMESPACE) && text.contains("Item:Semantic=\"GainMap\"") &&
                    attribute(text, "Version", "1.0") >= 0) container = true;
        }
        if (!container) return new int[0];
        Image gainmap = inspect(bytes, primary.end);
        if (gainmap == null) return new int[0];
        int position = -1;
        for (int[] range : gainmap.xmp) {
            String text = new String(bytes, range[0], range[1] - range[0], StandardCharsets.ISO_8859_1);
            if (!text.contains(NAMESPACE)) continue;
            if (position >= 0) return new int[0];
            for (String[] field : new String[][]{
                    {"Version", "1.0"}, {"GainMapMin", "0"}, {"GainMapMax", "0"},
                    {"Gamma", "1"}, {"OffsetSDR", "0"}, {"OffsetHDR", "0"},
                    {"HDRCapacityMin", "0"}, {"BaseRenditionIsHDR", "False"}}) {
                if (attribute(text, field[0], field[1]) < 0) return new int[0];
            }
            int offset = attribute(text, "HDRCapacityMax", "0");
            if (offset < 0) return new int[0];
            position = range[0] + offset;
        }
        if (position < 0 || primary.iso.size() > 1 || gainmap.iso.size() > 1) return new int[0];
        if (primary.iso.isEmpty() && gainmap.iso.isEmpty()) return new int[]{position};
        if (primary.iso.size() != 1 || gainmap.iso.size() != 1) return new int[0];
        int[] header = primary.iso.get(0);
        if (header[1] - header[0] != 4) return new int[0];
        for (int i = header[0]; i < header[1]; i++) if (bytes[i] != 0) return new int[0];
        // ISO 21496-1 version 0, one channel, base color space, common denominator
        // 1, zero gain and offsets, gamma 1. Admit exactly the observed neutral layout.
        int[] iso = gainmap.iso.get(0);
        if (iso[1] - iso[0] != 37) return new int[0];
        for (int i = 0; i < 37; i++) {
            int expected = i == 4 ? 0x48 : ((i == 8 || i == 28) ? 1 : 0);
            if ((bytes[iso[0] + i] & 255) != expected) return new int[0];
        }
        return new int[]{position, iso[0] + 16};
    }
}
