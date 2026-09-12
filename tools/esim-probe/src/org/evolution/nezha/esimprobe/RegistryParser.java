package org.evolution.nezha.esimprobe;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Parses only the defined GET STATUS/GET DATA registry template fields. */
final class RegistryParser {
    static final int MAX_BYTES = 65536;
    static final int MAX_ENTRIES = 256;

    static final class Entry {
        final byte[] aid;
        final byte[] lifecycle;
        Entry(byte[] aid, byte[] lifecycle) {
            this.aid = aid;
            this.lifecycle = lifecycle;
        }
    }

    private static final class Tlv {
        final int tag;
        final int start;
        final int end;
        Tlv(int tag, int start, int end) {
            this.tag = tag;
            this.start = start;
            this.end = end;
        }
    }

    private static Tlv read(byte[] data, int position, int limit) {
        if (position >= limit) throw new IllegalArgumentException("Missing TLV tag");
        int tag = data[position++] & 255;
        if ((tag & 31) == 31) {
            int count = 1;
            int next;
            do {
                if (position >= limit || count++ >= 3) {
                    throw new IllegalArgumentException("Truncated or oversized TLV tag");
                }
                next = data[position++] & 255;
                tag = (tag << 8) | next;
            } while ((next & 128) != 0);
        }
        if (position >= limit) throw new IllegalArgumentException("Missing TLV length");
        int length = data[position++] & 255;
        if ((length & 128) != 0) {
            int count = length & 127;
            if (count == 0 || count > 3 || count > limit - position) {
                throw new IllegalArgumentException("Invalid definite TLV length");
            }
            length = 0;
            for (int i = 0; i < count; i++) length = (length << 8) | (data[position++] & 255);
        }
        if (length > limit - position) throw new IllegalArgumentException("TLV exceeds enclosing value");
        return new Tlv(tag, position, position + length);
    }

    static List<Entry> parse(byte[] data, boolean directory) {
        if (data.length > MAX_BYTES) throw new IllegalArgumentException("Registry exceeds byte limit");
        List<Entry> entries = new ArrayList<>();
        int position = 0;
        while (position < data.length) {
            Tlv template = read(data, position, data.length);
            position = template.end;
            if (template.tag != (directory ? 0x61 : 0xe3)) {
                throw new IllegalArgumentException("Unexpected registry template");
            }
            byte[] aid = null;
            byte[] lifecycle = null;
            boolean privilegesPresent = false;
            int childPosition = template.start;
            while (childPosition < template.end) {
                Tlv child = read(data, childPosition, template.end);
                childPosition = child.end;
                if (child.tag == 0x4f) {
                    int length = child.end - child.start;
                    if (aid != null || length < 5 || length > 16) {
                        throw new IllegalArgumentException("Invalid or duplicate registry AID");
                    }
                    aid = Arrays.copyOfRange(data, child.start, child.end);
                } else if (!directory && child.tag == 0x9f70) {
                    if (lifecycle != null || child.end - child.start != 1) {
                        throw new IllegalArgumentException("Invalid or duplicate lifecycle field");
                    }
                    lifecycle = Arrays.copyOfRange(data, child.start, child.end);
                } else if (!directory && child.tag == 0xc5) {
                    // GP 2.3.1 Table 11-36 specifies three privilege bytes in
                    // this GET STATUS response (not INSTALL input encoding).
                    if (privilegesPresent || child.end - child.start != 3) {
                        throw new IllegalArgumentException("Invalid or duplicate privileges field");
                    }
                    privilegesPresent = true;
                }
                // Unknown direct children are skipped within their validated lengths.
            }
            if (aid == null) throw new IllegalArgumentException("Registry template has no AID");
            if (!directory && (lifecycle == null || !privilegesPresent)) {
                throw new IllegalArgumentException("Registry template lacks lifecycle or privileges");
            }
            if (entries.size() >= MAX_ENTRIES) throw new IllegalArgumentException("Registry exceeds entry limit");
            entries.add(new Entry(aid, lifecycle));
        }
        return entries;
    }
}
