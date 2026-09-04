/*
 * No-key regression fixture for SignApk's STORED-entry metadata/alignment path.
 * Run separately from the Python offline suite with an inert input ZIP. This
 * does not compile Android SignApk, sign an APK, or read a private key.
 */
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.jar.JarOutputStream;

public class SignApkStoredEntryTimestampRepro {
    private static JarEntry copyStoredEntry(JarEntry inEntry, boolean fresh) {
        if (fresh) {
            // Copy payload metadata without inheriting access/creation timestamps.
            // JarOutputStream can emit those as unaccounted extra fields and break alignment.
            JarEntry outEntry = new JarEntry(inEntry.getName());
            outEntry.setMethod(inEntry.getMethod());
            outEntry.setSize(inEntry.getSize());
            outEntry.setCompressedSize(inEntry.getCompressedSize());
            outEntry.setCrc(inEntry.getCrc());
            return outEntry;
        }
        return new JarEntry(inEntry);
    }

    private static void copy(Path input, Path output, boolean fresh, int alignment)
            throws Exception {
        long offset = 0;
        boolean firstEntry = true;
        try (JarFile in = new JarFile(input.toFile());
                OutputStream file = Files.newOutputStream(output, StandardOpenOption.CREATE_NEW);
                JarOutputStream out = new JarOutputStream(file)) {
            ArrayList<String> names = new ArrayList<>();
            var entries = in.entries();
            while (entries.hasMoreElements()) {
                names.add(entries.nextElement().getName());
            }
            Collections.sort(names);
            for (String name : names) {
                JarEntry inEntry = in.getJarEntry(name);
                if (inEntry.getMethod() != JarEntry.STORED || !name.matches("[ -~]+")) {
                    throw new IllegalArgumentException("fixture requires ASCII STORED entries");
                }
                JarEntry outEntry = copyStoredEntry(inEntry, fresh);
                outEntry.setTime(1230768000000L); // 2009-01-01 UTC; existing normalized timestamp.
                outEntry.setComment(null);
                outEntry.setExtra(null);

                // Same arithmetic as SignApk: local header, name, initial JAR magic, and padding.
                offset += JarFile.LOCHDR + outEntry.getName().length();
                if (firstEntry) {
                    offset += 4;
                    firstEntry = false;
                }
                long paddingStartOffset = offset + 6;
                int padding = (alignment - (int) (paddingStartOffset % alignment)) % alignment;
                byte[] extra = new byte[6 + padding];
                ByteBuffer extraBuf = ByteBuffer.wrap(extra).order(ByteOrder.LITTLE_ENDIAN);
                extraBuf.putShort((short) 0xd935);
                extraBuf.putShort((short) (2 + padding));
                extraBuf.putShort((short) alignment);
                outEntry.setExtra(extra);
                offset += extra.length;

                out.putNextEntry(outEntry);
                try (InputStream data = in.getInputStream(inEntry)) {
                    data.transferTo(out);
                }
                out.closeEntry();
                offset += inEntry.getSize();
            }
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            throw new IllegalArgumentException("input.zip output-directory alignment");
        }
        int alignment = Integer.parseInt(args[2]);
        if (alignment != 4 && alignment != 4096) {
            throw new IllegalArgumentException("fixture supports 4-byte or 4-KiB alignment");
        }
        Path directory = Path.of(args[1]);
        Files.createDirectory(directory);
        copy(Path.of(args[0]), directory.resolve("cloned.zip"), false, alignment);
        copy(Path.of(args[0]), directory.resolve("fresh.zip"), true, alignment);
    }
}
