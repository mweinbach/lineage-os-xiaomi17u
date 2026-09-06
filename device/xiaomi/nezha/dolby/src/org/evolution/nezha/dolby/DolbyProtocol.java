// SPDX-License-Identifier: Apache-2.0
package org.evolution.nezha.dolby;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/** Independently authored encoding of the inspected vendor effect interface. */
final class DolbyProtocol {
    static final int ENABLE = 0;
    static final int PROFILE_COUNT = 0x03000000;
    static final int CURRENT_PROFILE = 0x0a000000;
    static final int SET_KEY = 5;
    static final int MAX_PROFILES = 32;

    private DolbyProtocol() {}

    static byte[] query(int parameter) {
        return packet(parameter, 0, 0);
    }

    static byte[] change(int parameter, int value) {
        if (parameter != ENABLE && parameter != CURRENT_PROFILE) {
            throw new IllegalArgumentException("Unsupported writable parameter");
        }
        return packet(parameter, 1, value);
    }

    private static byte[] packet(int parameter, int operation, int value) {
        return ByteBuffer.allocate(12).order(ByteOrder.LITTLE_ENDIAN)
                .putInt(parameter).putInt(operation).putInt(value).array();
    }

    static int decode(byte[] response, int returnedBytes) {
        if (returnedBytes < Integer.BYTES || returnedBytes > response.length) {
            throw new IllegalStateException("Invalid effect response length/status: " + returnedBytes);
        }
        return ByteBuffer.wrap(response).order(ByteOrder.LITTLE_ENDIAN).getInt();
    }

    static void checkStatus(String operation, int status) {
        if (status != 0) {
            throw new IllegalStateException(operation + " failed, status " + status);
        }
    }

    static void checkProfiles(int count, int current) {
        if (count < 1 || count > MAX_PROFILES || current < 0 || current >= count) {
            throw new IllegalStateException("Invalid profile state: count=" + count + ", current=" + current);
        }
    }

    static String knownProfileName(int id) {
        switch (id) {
            case 0: return "Dynamic";
            case 1: return "Movie";
            case 2: return "Music";
            case 3: return "Custom";
            case 4: return "Mobility_default";
            case 5: return "Mobility_on_the_go";
            case 6: return "Mobility_commute";
            case 7: return "Mobility_travel";
            case 8: return "Voice";
            default: return null;
        }
    }
}
