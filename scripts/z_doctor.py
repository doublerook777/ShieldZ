"""Check that this environment matches the LinuxONE image (M0 gate, and every Z gate).

On the VM:   make z-doctor
On a laptop: python scripts/z_doctor.py --local   (skips the s390x and llama_cpp checks)
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as md
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PINS = ROOT / "requirements" / "z-preinstalled.txt"
Z_ONLY_IMPORTS = ["llama_cpp"]
IMPORTS = ["xgboost", "numpy", "pandas", "sklearn", "onnx"]


def read_pins(path: Path) -> dict[str, str]:
    pins = {}
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if "==" in line:
            name, version = line.split("==", 1)
            pins[name.strip().lower()] = version.strip()
    return pins


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="laptop run: skip s390x and llama_cpp")
    args = ap.parse_args()

    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    machine = platform.machine()
    if not args.local:
        check("platform is s390x", machine == "s390x", machine)
    check("python 3.12", sys.version_info[:2] == (3, 12), platform.python_version())

    for mod in IMPORTS + ([] if args.local else Z_ONLY_IMPORTS):
        try:
            importlib.import_module(mod)
            check(f"import {mod}", True)
        except Exception as exc:  # noqa: BLE001 - report any import failure
            check(f"import {mod}", False, repr(exc))

    for name, want in read_pins(PINS).items():
        try:
            have = md.version(name)
        except md.PackageNotFoundError:
            check(f"{name}=={want}", False, "not installed")
            continue
        check(f"{name}=={want}", have == want, f"installed {have}")

    artifacts = ROOT / "artifacts"
    try:
        artifacts.mkdir(exist_ok=True)
        probe = artifacts / ".doctor_probe"
        probe.write_text("ok")
        probe.unlink()
        check("artifacts/ writable", True, str(artifacts))
    except OSError as exc:
        check("artifacts/ writable", False, repr(exc))

    free_gb = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize / 1e9
    check("free disk >= 10 GB", free_gb >= 10, f"{free_gb:.1f} GB")

    width = max(len(n) for n, _, _ in results)
    for name, ok, detail in results:
        print(f"{'OK  ' if ok else 'FAIL'} {name:<{width}}  {detail}")
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{'ALL OK' if not failed else f'{len(failed)} FAILED'} on {machine}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
