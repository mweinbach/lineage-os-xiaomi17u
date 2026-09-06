#!/usr/bin/env python3
"""Prepare the exact Nezha normal-brightness packet, offline and without a phone.

HBM is deliberately withheld: the pinned framework does not consume the stock
legacy thermal limit, and its zero-duration timer would repeatedly reschedule.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

if __package__:
    from .artifact_files import publish_new_directory
    from .camera_apk_inputs import Reader
else:
    from artifact_files import publish_new_directory
    from camera_apk_inputs import Reader

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "vendor/xiaomi/nezha-display"
DISPLAY = "display_id_4630946639341352083.xml"
OVERLAY = "overlay/frameworks/base/core/res/res/values/brightness.xml"
PANEL_HASH = "71949a144918a4e31036806d213aba4d3454c06348d578a9bdf810b9463d9605"
PRODUCT_HASH = "67e6c683c1091abc0a548c27e4681bbe26471529129d15453b95c8d69417795f"
INPUTS = {
    "device-config/files/0002": PANEL_HASH,
    "product-overlays/files/0001": "330ff07784e3112e6aa118626aa9b94aa86345868bc0f54e27dd129142d0bd36",
    "product-overlays/files/0003": "f17075199a2c98f9a292bd063b2d43779837bc2914beaf838904de3c038cf702",
    "product-overlays/0001-resources.txt": "70a9fd7a3afa5f7f7f4caa31755fe28deee447a5f129c7f1e12db7fff64798b2",
    "product-overlays/0003-resources.txt": "f6541adc51080e63bdbf604e7b925015a0dc28411f1010de8722b2053cb911a0",
    "overlay-validation/evolution-core_res_res_values_config.xml": "b7c169c6ce96e3e76617eb2e253e74deac4c3a1e9822025d5ba7443db235e0ba",
}
RECEIPT_PATHS = {
    "device-config": {"files/0002": "/etc/displayconfig/" + DISPLAY},
    "product-overlays": {"files/0001": "/overlay/AospFrameworkResOverlay.apk",
                         "files/0003": "/overlay/FrameworksResCommon_Sys.apk"},
}
OUTPUT_HASHES = {
    DISPLAY: "ae025443ec514cdc9fb4fae29586d754cea1f7967b3529f5aff815deba563b92",
    OVERLAY: "f321d9919dfb1a5efd5f85f9d0a79d635a1757a308ad95596e91282aadb52439",
    "display-product.mk": "5a26386768f78bc20a5650a9a83f6960e9ec341c747fee1cccc2351971e9ae44",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def decimal(value):
    result = Decimal(value)
    require(result.is_finite(), "non-finite display value")
    return result


def number(value):
    return format(value.quantize(Decimal("0.000000001")), "f").rstrip("0").rstrip(".") or "0"


def resource(dump, kind, name):
    pattern = rf"^    resource [^\n]+ {kind}/{name}\n(.*?)(?=^    resource |^  type |\Z)"
    matches = re.findall(pattern, dump, re.M | re.S)
    require(len(matches) == 1, "missing or ambiguous stock resource: " + name)
    body = matches[0]
    if kind == "array":
        match = re.fullmatch(r"\s+\(\) \(array\) size=(\d+)\s+\[([^\]]*)\]\s*", body)
        require(match is not None, "unsupported array resource: " + name)
        values = [v.strip() for v in match[2].split(",") if v.strip()]
        require(len(values) == int(match[1]), "array length mismatch: " + name)
        return values
    match = re.fullmatch(r"\s+\(\) ([^\n]+)\s*", body)
    require(match is not None, "qualified stock resource: " + name)
    return match[1].strip()


def calibration(panel, dump, common, framework):
    root = ET.fromstring(panel)
    require(root.tag == "displayConfiguration", "wrong display root")
    points = [(decimal(p.findtext("value")), decimal(p.findtext("nits")))
              for p in root.findall("screenBrightnessMap/point")]
    require(len(points) == 9 and all(a[0] < b[0] and a[1] < b[1]
            for a, b in zip(points, points[1:])), "invalid exact-panel calibration")
    hbm = root.find("highBrightnessMode")
    require(hbm is not None and hbm.get("enabled") == "true", "missing stock HBM")
    cap = decimal(hbm.findtext("transitionPoint"))
    minimum = decimal(resource(dump, "dimen", "config_screenBrightnessSettingMinimumFloat"))
    default = decimal(resource(dump, "dimen", "config_screenBrightnessSettingDefaultFloat"))
    require(points[0][0] == minimum and minimum <= default < cap < points[-1][0],
            "stock brightness constraints do not cover the panel map")
    # DDC.rawBacklightToNits uses linear interpolation at a constrained endpoint.
    segment = next((a, b) for a, b in zip(points, points[1:]) if a[0] <= cap <= b[0])
    a, b = segment
    cap_nits = a[1] + (b[1] - a[1]) * (cap - a[0]) / (b[0] - a[0])
    # DDC rescales the constrained backlight range to framework brightness 0..1.
    normalized_default = (default - minimum) / (cap - minimum)
    lux = [decimal(v) for v in resource(dump, "array", "config_autoBrightnessLevels")]
    nits = [decimal(v) for v in resource(dump, "array", "config_autoBrightnessDisplayValuesNits")]
    require(len(lux) == 132 and len(nits) == len(lux) + 1 and lux[0] > 0
            and all(a < b for a, b in zip(lux, lux[1:]))
            and nits[0] >= 0 and all(a <= b for a, b in zip(nits, nits[1:])),
            "invalid auto-brightness physical mapping")
    require(resource(common, "bool", "config_automatic_brightness_available") == "true",
            "stock automatic brightness disabled")
    overlay = ET.Element("resources")
    ET.SubElement(overlay, "bool", name="config_automatic_brightness_available").text = "true"
    values = {
        "config_screenBrightnessSettingMinimumFloat": minimum,
        "config_screenBrightnessSettingMaximumFloat": cap,
        "config_screenBrightnessSettingDefaultFloat": normalized_default,
        "config_screenBrightnessDimFloat": Decimal(0),
    }
    for name, value in values.items():
        ET.SubElement(overlay, "item", name=name, type="dimen", format="float").text = number(value)
    for name in ("config_autoBrightnessBrighteningLightDebounce", "config_autoBrightnessDarkeningLightDebounce"):
        ET.SubElement(overlay, "integer", name=name).text = resource(dump, "integer", name)
    for name, tag, data in (("config_autoBrightnessLevels", "integer-array", lux),
                            ("config_autoBrightnessDisplayValuesNits", "array", [min(n, cap_nits) for n in nits])):
        element = ET.SubElement(overlay, tag, name=name)
        for value in data:
            # TypedArray.getFloat requires float items even for integral nits.
            text = number(value)
            ET.SubElement(element, "item").text = text + (".0" if tag == "array" and "." not in text else "")
    definitions = {e.get("name"): e for e in ET.fromstring(framework) if e.get("name")}
    for e in overlay:
        definition = definitions.get(e.get("name"))
        require(definition is not None and definition.tag == e.tag
                and definition.get("type") == e.get("type"), "pinned framework resource incompatible: " + e.get("name"))
    root.remove(hbm)
    ET.SubElement(root, "screenBrightnessDefault").text = number(normalized_default)
    ET.indent(root, space="    ")
    ET.indent(overlay, space="    ")
    metadata = {"normal_backlight_ceiling": str(cap), "normal_nits_ceiling": number(cap_nits),
                "normalized_default": number(normalized_default), "stock_default_backlight": str(default),
                "stock_minimum_backlight": str(minimum), "hbm_enabled": False,
                "auto_curve_points": len(nits), "auto_curve_capped_points": sum(n > cap_nits for n in nits)}
    return {DISPLAY: ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n",
            OVERLAY: ET.tostring(overlay, encoding="utf-8", xml_declaration=True) + b"\n"}, metadata


def render_make(files):
    lines = ["# Generated exact Nezha normal-brightness packet; HBM withheld.",
             "# Missing or changed calibration/resources are fatal, including at Make parse time."]
    for name, raw in sorted(files.items()):
        path = NAMESPACE + "/" + name
        lines += [f"ifneq ($(strip $(shell sha256sum {path} 2>/dev/null | cut -d' ' -f1)),{sha(raw)})",
                  f"$(error Nezha display packet missing or changed: {path})", "endif"]
    lines += [f"DEVICE_PACKAGE_OVERLAYS := {NAMESPACE}/overlay $(DEVICE_PACKAGE_OVERLAYS)",
              f"PRODUCT_COPY_FILES += {NAMESPACE}/{DISPLAY}:$(TARGET_COPY_OUT_PRODUCT)/etc/displayconfig/{DISPLAY}", ""]
    return "\n".join(lines).encode()


def prepare(stock, output):
    stock, output = Path(stock), Path(output).absolute()
    require(output.is_relative_to(ROOT / "artifacts") and ".." not in output.parts,
            "private display packet output must be below this worktree's ignored artifacts directory")
    reader = Reader()
    files = {}
    for name, expected in INPUTS.items():
        raw = reader.read(stock / name, maximum=16 * 1024 * 1024)
        require(sha(raw) == expected, "retained stock/source hash mismatch: " + name)
        files[name] = raw
    for folder, expected_files in RECEIPT_PATHS.items():
        receipt = json.loads(reader.read(stock / folder / "receipt.json"))
        require(receipt["image"]["sha256"] == PRODUCT_HASH and receipt["operation"] == "erofs-capture",
                "wrong factory product provenance")
        for name, path in expected_files.items():
            records = [e for e in receipt["files"] if e.get("output_path") == name]
            require(len(records) == 1, "ambiguous capture path")
            e, raw = records[0], files[folder + "/" + name]
            require(e.get("path") == path and e.get("type") == "regular"
                    and e.get("readback_verified") is True and e.get("sha256") == sha(raw)
                    and e.get("size_bytes") == len(raw), "capture receipt path/hash mismatch")
    outputs, details = calibration(files["device-config/files/0002"],
        files["product-overlays/0001-resources.txt"].decode(),
        files["product-overlays/0003-resources.txt"].decode(),
        files["overlay-validation/evolution-core_res_res_values_config.xml"])
    outputs["display-product.mk"] = render_make(outputs)
    require({name: sha(raw) for name, raw in outputs.items()} == OUTPUT_HASHES,
            "derived outputs differ from reviewed normal-brightness contract")
    receipt = {"schema_version": 1, "contract": "nezha-normal-brightness-v1", "inputs": INPUTS,
               "details": details, "outputs": {name: sha(raw) for name, raw in outputs.items()},
               "native_build_verified": False, "phone_accessed": False}
    outputs["display-panel-inputs.json"] = encoded(receipt)
    require(not output.exists() and not output.is_symlink(), "output already exists")
    # The caller creates the parent explicitly; never resolve through a symlink.
    for ancestor in [*reversed(output.parent.parents), output.parent]:
        require(ancestor.is_dir() and not ancestor.is_symlink(), "unsafe output ancestor")
    staging = Path(tempfile.mkdtemp(prefix=".nezha-display-", dir=output.parent))
    try:
        for name, raw in outputs.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        reader.recheck()
        publish_new_directory(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return receipt


def verify_delivery(target_files, packet):
    """Check final target-files bytes, not just PRODUCT_COPY_FILES declarations."""
    import zipfile
    reader = Reader()
    receipt = json.loads(reader.read(Path(packet) / "display-panel-inputs.json"))
    raw = reader.read(Path(packet) / DISPLAY)
    require(receipt.get("contract") == "nezha-normal-brightness-v1"
            and receipt.get("inputs") == INPUTS
            and receipt.get("outputs") == OUTPUT_HASHES
            and OUTPUT_HASHES[DISPLAY] == sha(raw), "invalid panel packet receipt")
    for name, expected in OUTPUT_HASHES.items():
        require(sha(reader.read(Path(packet) / name)) == expected, "panel packet output changed: " + name)
    member = "PRODUCT/etc/displayconfig/" + DISPLAY
    with zipfile.ZipFile(target_files) as archive:
        entries = [e for e in archive.infolist() if e.filename == member]
        require(len(entries) == 1 and entries[0].file_size == len(raw), "missing/duplicate/wrong-sized delivered panel")
        require(archive.read(entries[0]) == raw, "delivered panel hash mismatch")
    return {"target_files_panel_delivered": True, "sha256": sha(raw),
            "framework_resource_delivery_verified": False, "device_behavior_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--stock", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p = sub.add_parser("verify-delivery")
    p.add_argument("--target-files", required=True, type=Path)
    p.add_argument("--packet", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.stock, args.output) if args.command == "prepare" else verify_delivery(args.target_files, args.packet)
        print(encoded(result).decode(), end="")
        return 0
    except (ValueError, OSError, KeyError, ET.ParseError) as error:
        print("display-panel-inputs: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
