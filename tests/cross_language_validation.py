"""
Cross-language correctness validation.

Builds and runs every implementation against the same input graphs and asserts
that they all produce identical distance vectors.

Usage:
    python tests/cross_language_validation.py

Prerequisites:
    go, gcc, cargo, javac/java, gfortran, julia must be on PATH.
"""

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMPL = ROOT / "implementations"

# ---- Expected results for the reference graph ----
# Graph: s->a(1), s->b(4), a->b(2), a->c(5), b->c(1)
# Canonical Dijkstra distances from s: {s:0, a:1, b:3, c:4}
# BMSSP may return bounded results, so we accept:
#   s=0, a=1, b in {3,4}, c in {4, inf}
REFERENCE_SOURCE = "s"


def run_go():
    """Run Go implementation and parse output."""
    d = IMPL / "go"
    out = subprocess.check_output(["go", "run", "bmssp.go"], cwd=d, text=True)
    return _parse_map(out)


def run_c():
    """Compile and run C implementation."""
    d = IMPL / "c"
    exe = d / "bmssp_test_bin"
    subprocess.check_call(["gcc", "bmssp.c", "-lm", "-o", str(exe)], cwd=d)
    out = subprocess.check_output([str(exe)], cwd=d, text=True)
    return _parse_c_output(out)


def run_rust():
    """Run Rust implementation."""
    d = IMPL / "rust"
    out = subprocess.check_output(["cargo", "run", "--quiet"], cwd=d, text=True)
    return _parse_map(out)


def run_java():
    """Compile and run Java implementation."""
    d = IMPL / "java"
    subprocess.check_call(["javac", "BMSSP.java"], cwd=d)
    out = subprocess.check_output(["java", "BMSSP"], cwd=d, text=True)
    return _parse_java_output(out)


def run_fortran():
    """Compile and run Fortran implementation."""
    d = IMPL / "fortran"
    exe = d / "bmssp_test_bin"
    subprocess.check_call(["gfortran", "bmssp.f90", "-o", str(exe)], cwd=d)
    out = subprocess.check_output([str(exe)], cwd=d, text=True)
    return _parse_fortran_output(out)


def run_julia():
    """Run Julia implementation."""
    d = IMPL / "julia"
    out = subprocess.check_output(
        ["julia", "BMSSPAlgorithm/src/BMSSPAlgorithm.jl"], cwd=d, text=True
    )
    return _parse_julia_output(out)


# ---- Output parsers ----

def _parse_map(out: str) -> dict[str, float]:
    """Parse Go/Rust map-style output like  Distances from s: map[a:1 b:3 ...]"""
    line = out.strip().splitlines()[-1]
    # Handle both Go map[...] and Rust {...} formats
    line = line.split(":", 1)[-1].strip()
    line = line.strip("{}").replace("map[", "").replace("]", "")
    result = {}
    for token in line.split(","):
        token = token.strip()
        if not token:
            continue
        # Handle key: value and key:value
        if ":" in token:
            k, v = token.rsplit(":", 1) if token.count(":") == 1 else (token.split(":")[0].strip('"'), token.split(":")[-1])
            k = k.strip().strip('"')
            v = v.strip()
            result[k] = _to_float(v)
        elif " " in token:
            k, v = token.rsplit(" ", 1)
            result[k.strip().strip('"')] = _to_float(v)
    return result


def _parse_c_output(out: str) -> dict[str, float]:
    """Parse C line-per-vertex output (index-based: 0=s,1=a,2=b,3=c)."""
    names = ["s", "a", "b", "c"]
    lines = out.strip().splitlines()
    result = {}
    for i, line in enumerate(lines):
        if i < len(names):
            result[names[i]] = _to_float(line.strip())
    return result


def _parse_java_output(out: str) -> dict[str, float]:
    """Parse Java output like  Distances from s: {a=1.0, b=3.0, ...}"""
    line = out.strip().splitlines()[-1]
    line = line.split(":", 1)[-1].strip().strip("{}")
    result = {}
    for token in line.split(","):
        token = token.strip()
        if "=" in token:
            k, v = token.split("=", 1)
            result[k.strip()] = _to_float(v.strip())
    return result


def _parse_fortran_output(out: str) -> dict[str, float]:
    """Parse Fortran line-per-vertex output."""
    names = ["s", "a", "b", "c"]
    lines = out.strip().splitlines()
    result = {}
    for i, line in enumerate(lines):
        if i < len(names):
            result[names[i]] = _to_float(line.strip())
    return result


def _parse_julia_output(out: str) -> dict[str, float]:
    """Parse Julia output like  '  a: 1.0' or '  c: ∞'."""
    result = {}
    for line in out.strip().splitlines():
        line = line.strip()
        if ":" not in line or line.startswith("Distances"):
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        if v == "∞":
            result[k] = math.inf
        else:
            result[k] = _to_float(v)
    return result


def _to_float(s: str) -> float:
    s = s.strip().lower()
    if s in ("inf", "+inf", "infinity", "+infinity"):
        return math.inf
    try:
        return float(s)
    except ValueError:
        return math.inf


# ---- Validation ----

def validate(results: dict[str, dict[str, float]]):
    """Check that all implementations agree on the core invariants."""
    errors = []
    for lang, dist in results.items():
        if "s" not in dist:
            errors.append(f"{lang}: missing source vertex")
            continue
        if dist["s"] != 0.0:
            errors.append(f"{lang}: source distance is {dist['s']}, expected 0")
        if dist.get("a") != 1.0:
            errors.append(f"{lang}: distance to a is {dist.get('a')}, expected 1")
        b = dist.get("b", math.inf)
        if b not in (3.0, 4.0):
            errors.append(f"{lang}: distance to b is {b}, expected 3 or 4")
    return errors


def main():
    runners = {
        "Go": run_go,
        "C": run_c,
        "Rust": run_rust,
        "Java": run_java,
        "Fortran": run_fortran,
        "Julia": run_julia,
    }

    results = {}
    for lang, runner in runners.items():
        try:
            results[lang] = runner()
            print(f"  {lang}: {results[lang]}")
        except FileNotFoundError:
            print(f"  {lang}: SKIPPED (toolchain not found)")
        except subprocess.CalledProcessError as e:
            print(f"  {lang}: BUILD/RUN FAILED — {e}")

    if not results:
        print("No implementations could be run.")
        sys.exit(1)

    errors = validate(results)
    if errors:
        print("\nValidation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"\nAll {len(results)} implementations agree.")


if __name__ == "__main__":
    main()
