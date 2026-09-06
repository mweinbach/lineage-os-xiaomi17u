#!/usr/bin/env python3
"""Execute the exact IMS compatibility patch on a host JVM with property doubles.

This optional validation needs a local JDK. Required unittest coverage mocks the
compiler and JVM; no Android source checkout, network or phone is required.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

WORKSPACE = Path(__file__).resolve().parents[1]
METADATA = "patches/evolution/nezha-ims-telephony-api.json"


def source_from_patch(workspace=WORKSPACE):
    record = json.loads((workspace / METADATA).read_text())
    patch = (workspace / record["patch"]).read_bytes()
    if hashlib.sha256(patch).hexdigest() != record["patch_sha256"]:
        raise ValueError("IMS API patch digest mismatch")
    target = record["file"]
    path = target["path"]
    header = (f"diff --git a/{path} b/{path}\nnew file mode 100644\n"
              f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{target['lines']} @@\n")
    if not patch.startswith(header.encode()):
        raise ValueError("Unexpected IMS API patch header")
    lines = patch[len(header):].decode().splitlines(keepends=True)
    if len(lines) != target["lines"] or any(not line.startswith("+") for line in lines):
        raise ValueError("Unexpected IMS API patch body")
    source = "".join(line[1:] for line in lines)
    if hashlib.sha256(source.encode()).hexdigest() != target["after_sha256"]:
        raise ValueError("IMS API source digest mismatch")
    return source


def verify_source_basis(source, workspace=WORKSPACE):
    """Read-only applicability check on the selected framework control files."""
    record = json.loads((workspace / METADATA).read_text())
    source = Path(source)
    for name, expected in record["source_basis"].items():
        path = source / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("IMS API source basis differs: " + name)
    target = source / record["file"]["path"]
    if target.exists() or target.is_symlink():
        raise ValueError("IMS API target already exists; review the existing implementation")
    return {"source_basis_verified": True, "source_changed": False,
            "source_revision_expected": record["revision"], "activation_allowed": False}


def run_validation(root, source):
    files = {
        "android/os/SystemProperties.java": '''package android.os;
import java.util.*;
public final class SystemProperties {
    public static final Map<String,String> values = new HashMap<>();
    public static final List<String> reads = new ArrayList<>();
    public static String get(String key, String defaultValue) {
        if (!defaultValue.equals("")) throw new AssertionError("Wrong property default");
        reads.add(key);
        return values.getOrDefault(key, defaultValue);
    }
}''',
        "android/telephony/TelephonyBaseUtilsStub.java": source,
        "fixture/ImsApiHarness.java": '''package fixture;
import android.os.SystemProperties;
import android.telephony.TelephonyBaseUtilsStub;
import java.lang.reflect.Modifier;
import java.util.List;
public final class ImsApiHarness {
    private static final String NAME = "ro.miui.ui.version.name";
    private static final String CODE = "ro.miui.ui.version.code";
    private static int assertions;
    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message);
    }
    private static void scenario(String name, String code, boolean expected) {
        SystemProperties.values.clear();
        SystemProperties.reads.clear();
        if (name != null) SystemProperties.values.put(NAME, name);
        if (code != null) SystemProperties.values.put(CODE, code);
        check(TelephonyBaseUtilsStub.isMiuiRom() == expected, "property result");
        check(SystemProperties.reads.get(0).equals(NAME), "name read first");
        if (name != null && !name.isEmpty()) {
            check(SystemProperties.reads.equals(List.of(NAME)), "short-circuit code read");
        } else {
            check(SystemProperties.reads.equals(List.of(NAME, CODE)), "code read with empty name");
        }
    }
    public static void main(String[] args) throws Exception {
        var cls = TelephonyBaseUtilsStub.class;
        var method = cls.getDeclaredMethod("isMiuiRom");
        check(Modifier.isPublic(method.getModifiers()) && Modifier.isStatic(method.getModifiers()),
              "public static ABI");
        check(method.getReturnType() == boolean.class && method.getParameterCount() == 0,
              "()Z ABI");
        check(cls.getDeclaredMethods().length == 1 && cls.getDeclaredFields().length == 0,
              "one method and no cached property fields");
        check(Modifier.isPrivate(cls.getDeclaredConstructor().getModifiers()), "private constructor");
        scenario(null, null, false);
        scenario("", "", false);
        scenario("V150", null, true);
        scenario(null, "15", true);
        scenario("OS3.0", "15", true);
        scenario("0", "", true);
        scenario("", "0", true);
        scenario("false", null, true);
        scenario(null, "false", true);
        scenario(" ", "", true);
        scenario("", " ", true);
        // Same loaded class observes changes; no result cached by an initializer.
        scenario(null, null, false);
        scenario(null, "15", true);
        scenario(null, null, false);
        scenario("V150", null, true);
        scenario("", "", false);
        System.out.println("PASS: " + assertions + " assertions; exact ABI, property truth table, "
                           + "short circuit, read order, empty defaults and repeated reads");
    }
}''',
    }
    for name, content in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    subprocess.run(["javac", "-d", str(root / "classes"),
                    *[str(root / name) for name in files]], check=True)
    subprocess.run(["java", "-cp", str(root / "classes"), "fixture.ImsApiHarness"], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="read-only framework source-basis verification")
    args = parser.parse_args()
    source = source_from_patch()
    if args.source:
        print(json.dumps(verify_source_basis(args.source), indent=2))
    with tempfile.TemporaryDirectory(prefix="nezha-ims-api-fixture-") as directory:
        run_validation(Path(directory), source)


if __name__ == "__main__":
    main()
