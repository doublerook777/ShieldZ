"""Does a PyPI package run on s390x? (invariant I8, DECISIONS.md "Adding a dependency")

Usage: python scripts/check_deps.py fastapi snapml==1.17.2

Verdicts: ok-wheel (s390x wheel), ok-pure (none-any wheel), sdist-only (needs a source build:
risky), or missing. Packages already in the L1CC image: requirements/z-preinstalled.txt.
This only looks at the python 3.12 wheels; it never installs anything.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def verdict(files: list[dict]) -> tuple[str, str]:
    names = [f["filename"] for f in files if not f.get("yanked")]
    s390x = [
        n
        for n in names
        if n.endswith(".whl") and "s390x" in n and any(t in n for t in ("cp312", "abi3", "py3"))
    ]
    if s390x:
        return "ok-wheel", s390x[0]
    pure = [n for n in names if n.endswith("-none-any.whl")]
    if pure:
        return "ok-pure", pure[0]
    if any(n.endswith((".tar.gz", ".zip")) for n in names):
        return "sdist-only", "no s390x wheel; pip would build from source"
    return "missing", "no usable files"


def check(spec: str) -> int:
    name, _, version = spec.partition("==")
    url = (
        f"https://pypi.org/pypi/{name}/{version}/json"
        if version
        else f"https://pypi.org/pypi/{name}/json"
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        print(f"missing    {spec}: PyPI returned {exc.code}")
        return 1
    files = data["urls"]
    kind, detail = verdict(files)
    print(f"{kind:<10} {name}=={data['info']['version']}: {detail}")
    return 0 if kind.startswith("ok") else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(max(check(s) for s in sys.argv[1:]))
