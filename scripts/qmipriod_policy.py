#!/usr/bin/env python3
"""Exact additive vendor policy for qmipriod's debug log, selected explicitly.

Keep the historical Binder correction immutable. This extension accepts only
that derivative and appends two reviewed rules; it neither compiles policy nor
relaxes a compiler check. The full extended CIL remains the compiler/image input.
"""
from __future__ import annotations

import json
from pathlib import Path

if __package__:
    from . import vendor_policy as vp
else:
    import vendor_policy as vp

CONTRACT_PATH = "config/nezha-qmipriod-policy.json"
CONTRACT_SHA256 = "2eadb0d5dc5062207f875aae64343d6e1b103fd31387683413a0cd14236e5911"


def load_contract(path=None, reader=None):
    reader = reader or vp.Reader()
    return json.loads(reader.read(path or Path(__file__).resolve().parents[1] / CONTRACT_PATH,
                                  CONTRACT_SHA256))


def _check(raw, expected):
    vp.require(len(raw) == expected["size_bytes"] and vp.sha(raw) == expected["sha256"],
               "qmipriod policy input or output differs from the reviewed identity")


def extend(base, contract):
    """Pure derivation; production callers load the hash-pinned contract first."""
    _check(base, contract["base"])
    result = base + contract["suffix"].encode("utf-8")
    _check(result, contract["output"])
    return result


def verify_extended(raw, contract):
    """Check the entire delivered input, then factor its separately checked base.

    Returning the base lets the existing OEM ownership model keep its original
    immutable budget. The full-byte output pin verifies that the only extra
    permissions are those in this contract, and secilc checks that full input.
    """
    _check(raw, contract["output"])
    suffix = contract["suffix"].encode("utf-8")
    vp.require(bool(suffix) and raw.endswith(suffix), "qmipriod policy suffix differs")
    base = raw[:-len(suffix)]
    _check(base, contract["base"])
    return base


def render_blueprint(raw):
    """Wire the same explicit contract into derivation and native verification."""
    text = raw.decode("utf-8")
    vp.require("qmipriod_policy" not in text, "qmipriod policy already selected")
    for main in ("vendor_policy.py", "oem_policy.py"):
        start = text.index('    main: "tools/' + main + '",')
        pos = text.index("    srcs: [", start)
        end = text.index("],", pos)
        text = text[:end] + ', "tools/qmipriod_policy.py"' + text[end:]
    source = '        "tools/vendor_policy.py",\n'
    vp.require(text.count(source) == 2, "expected derivation and native-check source lists")
    text = text.replace(source, source +
                        '        "tools/qmipriod_policy.py",\n'
                        '        "tools/nezha-qmipriod-policy.json",\n')
    for name in ("vendor-policy-correction.json", "nezha-oem-policy.json"):
        argument = '         "--contract $$(readlink -f $(location tools/' + name + ')) " +\n'
        vp.require(text.count(argument) == 1, "expected exact policy contract argument")
        text = text.replace(argument, argument +
                            '         "--qmipriod-contract $$(readlink -f $(location tools/nezha-qmipriod-policy.json)) " +\n')
    vp.require('ignore_neverallow: false,' in text, "strict policy compilation is required")
    return text.encode("utf-8")
