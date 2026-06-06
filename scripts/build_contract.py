#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
WHAT: Compile contracts/CoordinationReceipts.sol -> contracts/build/CoordinationReceipts.json (abi+bytecode).
WHY:  One-time build step shared by the local test + the deploy scripts.
HOW:  py-solc-x (solc 0.8.20). LINK: cairn/web3/celo.py, contracts/CoordinationReceipts.sol.
"""
import json, pathlib, solcx

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOL = ROOT / "contracts" / "CoordinationReceipts.sol"
OUT = ROOT / "contracts" / "build" / "CoordinationReceipts.json"
VER = "0.8.20"


def build():
    try:
        solcx.set_solc_version(VER)
    except Exception:
        solcx.install_solc(VER)
        solcx.set_solc_version(VER)
    compiled = solcx.compile_files([str(SOL)], output_values=["abi", "bin"], solc_version=VER)
    key = next(k for k in compiled if k.endswith(":CoordinationReceipts"))
    abi, bytecode = compiled[key]["abi"], compiled[key]["bin"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"abi": abi, "bytecode": bytecode}, indent=2))
    return abi, bytecode


if __name__ == "__main__":
    abi, bc = build()
    print(f"OK  compiled CoordinationReceipts -> {OUT.relative_to(ROOT)}  "
          f"({len(bc)} bytecode chars, {len(abi)} abi entries)")
