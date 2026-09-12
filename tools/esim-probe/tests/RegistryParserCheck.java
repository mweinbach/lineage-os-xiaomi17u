package org.evolution.nezha.esimprobe;

import java.io.ByteArrayOutputStream;
import java.util.Arrays;
import java.util.List;

/** Standalone host checks; no Android runtime or connected device required. */
public final class RegistryParserCheck {
    private static byte[] bytes(int... values) {
        byte[] result = new byte[values.length];
        for (int i = 0; i < values.length; i++) result[i] = (byte) values[i];
        return result;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void reject(byte[] body, boolean directory) {
        try { RegistryParser.parse(body, directory); }
        catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("Malformed or oversized input accepted");
    }

    private static byte[] registryWith(byte[]... fields) {
        ByteArrayOutputStream body = new ByteArrayOutputStream();
        byte[] aid = bytes(0x4f, 5, 0xa0, 0, 0, 1, 0x51);
        body.write(aid, 0, aid.length);
        for (byte[] field : fields) body.write(field, 0, field.length);
        require(body.size() < 128, "Fixture uses a short BER length");
        ByteArrayOutputStream template = new ByteArrayOutputStream();
        template.write(0xe3);
        template.write(body.size());
        template.write(body.toByteArray(), 0, body.size());
        return template.toByteArray();
    }

    public static void main(String[] args) {
        byte[] lifecycle = bytes(0x9f, 0x70, 1, 7);
        byte[] privileges = bytes(0xc5, 3, 0x80, 0, 0);
        byte[] registry = registryWith(lifecycle, privileges);
        List<RegistryParser.Entry> result = RegistryParser.parse(registry, false);
        require(result.size() == 1 && result.get(0).lifecycle[0] == 7, "Registry lifecycle");
        require(Arrays.equals(result.get(0).aid, bytes(0xa0, 0, 0, 1, 0x51)), "Registry AID");

        byte[] directory = bytes(0x61, 0x81, 12, 0x4f, 5, 0xa0, 0, 0, 1, 0x51, 0x50, 3, 0x4f, 1, 0);
        result = RegistryParser.parse(directory, true);
        require(result.size() == 1 && result.get(0).lifecycle == null, "Directory long length/unknown field");
        require(result.get(0).aid.length == 5, "Nested unrelated 4F must not replace direct AID");

        reject(registryWith(), false); // Neither mandatory GET STATUS field.
        reject(registryWith(lifecycle), false); // Missing privileges.
        reject(registryWith(privileges), false); // Missing lifecycle.
        reject(registryWith(lifecycle, privileges, privileges), false);
        reject(registryWith(lifecycle, lifecycle, privileges), false);
        for (int length : new int[] {0, 1, 2, 4}) {
            byte[] invalidPrivileges = new byte[2 + length];
            invalidPrivileges[0] = (byte) 0xc5;
            invalidPrivileges[1] = (byte) length;
            reject(registryWith(lifecycle, invalidPrivileges), false);
        }
        reject(registryWith(bytes(0x9f, 0x70, 0), privileges), false);
        reject(registryWith(bytes(0x9f, 0x70, 2, 7, 0), privileges), false);
        require(RegistryParser.parse(registryWith(privileges, lifecycle), false).size() == 1,
                "Mandatory fields may appear in either order");
        require(RegistryParser.parse(bytes(0x61, 7, 0x4f, 5, 1, 2, 3, 4, 5), true).size() == 1,
                "Directory requires neither lifecycle nor privileges");

        byte[] pair = new byte[registry.length * 2];
        System.arraycopy(registry, 0, pair, 0, registry.length);
        System.arraycopy(registry, 0, pair, registry.length, registry.length);
        require(RegistryParser.parse(pair, false).size() == 2, "Repeated registry templates");

        reject(Arrays.copyOf(registry, registry.length - 1), false);
        reject(bytes(0xe3, 0x80, 0, 0), false); // Indefinite length.
        reject(bytes(0xe3, 2, 0x4f, 5), false); // Child extends past parent.
        reject(bytes(0xe3, 6, 0x4f, 4, 1, 2, 3, 4), false); // AID too short.
        reject(bytes(0xe3, 14, 0x4f, 5, 1, 2, 3, 4, 5, 0x4f, 5, 1, 2, 3, 4, 5), false);
        reject(bytes(0xe3, 2, 0x50, 0), false); // Missing AID.
        reject(registry, true); // No inferred wrapper/template coercion.
        reject(new byte[RegistryParser.MAX_BYTES + 1], false);
        ByteArrayOutputStream many = new ByteArrayOutputStream();
        for (int i = 0; i <= RegistryParser.MAX_ENTRIES; i++) many.write(registry, 0, registry.length);
        reject(many.toByteArray(), false);
        System.out.println("RegistryParserCheck: valid data, scope, malformed lengths and bounds passed");
    }
}
