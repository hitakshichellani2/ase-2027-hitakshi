#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

TARGET_PYTHON = Version("3.11")
PYPI_URL = "https://pypi.org/pypi/{name}/{version}/json"


def read_requirements(path):
    """Return (name, version) pairs for every non-empty, non-comment line."""
    reqs = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if "==" in line:
                name, version = (part.strip() for part in line.split("==", 1))
            else:
                name, version = line, None
            reqs.append((name, version))
    return reqs


def fetch_release(name, version):
    """Return release JSON, or None if the package/version is not on PyPI."""
    url = PYPI_URL.format(name=name, version=version) if version else \
        f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def minimum_python(spec_set):
    """Lowest Python version a SpecifierSet allows (based on its lower bounds)."""
    lows = [Version(s.version.replace("*", "0").rstrip("."))
            for s in spec_set if s.operator in (">=", ">", "~=", "==")]
    return max(lows) if lows else Version("0")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    reqs = read_requirements(path)

    not_found = 0
    incompatible = 0
    highest = None  # (min_version, name, version, requires_python)

    for name, version in reqs:
        data = fetch_release(name, version)
        if data is None:
            not_found += 1
            continue

        requires_python = (data["info"].get("requires_python") or "").strip()
        if not requires_python:
            continue  # no requirement -> counts as compatible

        try:
            spec = SpecifierSet(requires_python)
        except InvalidSpecifier:
            continue  # unparseable metadata -> treat as no requirement

        if not spec.contains(TARGET_PYTHON, prereleases=True):
            incompatible += 1

        min_py = minimum_python(spec)
        if highest is None or min_py > highest[0]:
            highest = (min_py, name, version, requires_python)

    print(f"Dependencies checked: {len(reqs)}")
    print(f"Not found on PyPI: {not_found}")
    print(f"Incompatible with Python 3.11: {incompatible}")
    if highest:
        _, name, version, rp = highest
        print(f"Highest requirement: {name}=={version} ({rp})")
    else:
        print("Highest requirement: none")


if __name__ == "__main__":
    main()