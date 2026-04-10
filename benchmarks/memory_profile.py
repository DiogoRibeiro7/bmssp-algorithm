#!/usr/bin/env python3
"""
Memory Profiling for BMSSP Implementations

Measures peak memory (RSS) consumption for each compiled implementation
across varying graph sizes. Generates a markdown report and CSV data.

Usage:
  python benchmarks/memory_profile.py
  python benchmarks/memory_profile.py --sizes 100,1000,10000

Requires: psutil
"""

import csv
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Error: psutil required. Install with: pip install psutil", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
DOT_SAMPLE = REPO_ROOT / "docs" / "examples" / "sample.dot"

DEFAULT_SIZES = [100, 500, 1000, 5000, 10000]


def generate_dot(n, edge_factor=3, seed=42):
    """Generate a random sparse DOT graph with n nodes."""
    import random as rng
    rng.seed(seed)
    lines = ["digraph G {"]
    nodes = [f"n{i}" for i in range(n)]
    m = edge_factor * n
    for _ in range(m):
        u = rng.randint(0, n - 1)
        v = rng.randint(0, n - 1)
        if u != v:
            w = rng.randint(1, 100)
            lines.append(f"  {nodes[u]} -> {nodes[v]} [label={w}];")
    lines.append("}")
    return "\n".join(lines)


def measure_memory(cmd, cwd=None, timeout=120):
    """
    Run a command and measure peak RSS in MB.
    Returns (peak_rss_mb, runtime_s) or (None, None) on failure.
    """
    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        ps_proc = psutil.Process(proc.pid)

        peak_rss = 0
        start = time.monotonic()

        while proc.poll() is None:
            try:
                mem = ps_proc.memory_info()
                peak_rss = max(peak_rss, mem.rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(0.01)  # 10ms sampling

        elapsed = time.monotonic() - start
        proc.wait(timeout=10)

        if proc.returncode != 0:
            stderr = proc.stderr.read().decode()
            print(f"    Warning: {' '.join(cmd)} exited with {proc.returncode}: {stderr[:200]}")
            return None, None

        return peak_rss / (1024 * 1024), elapsed

    except Exception as e:
        print(f"    Error running {' '.join(cmd)}: {e}")
        return None, None


def build_implementations():
    """Build all compiled implementations, return dict of available binaries."""
    binaries = {}
    impl_dir = REPO_ROOT / "implementations"

    # C
    c_dir = impl_dir / "c"
    ext = ".exe" if platform.system() == "Windows" else ""
    result = subprocess.run(
        ["gcc", "-Wall", "-std=c11", "-O2", "bmssp.c", "-lm", "-o", f"bmssp{ext}"],
        cwd=c_dir, capture_output=True, text=True,
    )
    if result.returncode == 0:
        binaries["C"] = str(c_dir / f"bmssp{ext}")
    else:
        print(f"  C build failed: {result.stderr[:200]}")

    # Go
    go_dir = impl_dir / "go"
    result = subprocess.run(
        ["go", "build", "-o", f"bmssp_mem{ext}", "./cmd/bmssp/"],
        cwd=go_dir, capture_output=True, text=True,
    )
    if result.returncode == 0:
        binaries["Go"] = str(go_dir / f"bmssp_mem{ext}")
    else:
        print(f"  Go build failed: {result.stderr[:200]}")

    # Rust
    rust_dir = impl_dir / "rust"
    result = subprocess.run(
        ["cargo", "build", "--release"],
        cwd=rust_dir, capture_output=True, text=True, timeout=300,
    )
    if result.returncode == 0:
        binaries["Rust"] = str(rust_dir / "target" / "release" / f"bmssp{ext}")
    else:
        print(f"  Rust build failed: {result.stderr[:200]}")

    # Fortran
    f_dir = impl_dir / "fortran"
    result = subprocess.run(
        ["gfortran", "-std=f2008", "-O2", "bmssp.f90", "-o", f"bmssp{ext}"],
        cwd=f_dir, capture_output=True, text=True,
    )
    if result.returncode == 0:
        binaries["Fortran"] = str(f_dir / f"bmssp{ext}")
    else:
        print(f"  Fortran build failed: {result.stderr[:200]}")

    # Java (classpath)
    java_dir = impl_dir / "java"
    result = subprocess.run(
        ["javac", "BMSSP.java"], cwd=java_dir, capture_output=True, text=True,
    )
    if result.returncode == 0:
        binaries["Java"] = str(java_dir)  # directory with .class files
    else:
        print(f"  Java build failed: {result.stderr[:200]}")

    return binaries


def run_memory_profile(binaries, sizes):
    """Run memory profiling across all implementations and graph sizes."""
    results = []

    for n in sizes:
        print(f"\n  Graph size: n={n}")

        # Generate DOT file
        dot_content = generate_dot(n)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
            f.write(dot_content)
            dot_path = f.name

        try:
            for lang, binary in sorted(binaries.items()):
                if lang == "Java":
                    cmd = ["java", "-cp", binary, "BMSSP", dot_path, "n0"]
                else:
                    cmd = [binary, dot_path, "n0"]

                rss_mb, runtime_s = measure_memory(cmd)
                if rss_mb is not None:
                    results.append({
                        "language": lang,
                        "n": n,
                        "peak_rss_mb": round(rss_mb, 2),
                        "runtime_s": round(runtime_s, 3),
                    })
                    print(f"    {lang:<8} peak RSS: {rss_mb:>7.2f} MB  time: {runtime_s:.3f}s")
                else:
                    print(f"    {lang:<8} failed")
        finally:
            os.unlink(dot_path)

    return results


def generate_report(results, binaries):
    """Generate markdown memory profiling report."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "MEMORY_REPORT.md"
    csv_path = RESULTS_DIR / "memory_profile.csv"

    # Save CSV
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["language", "n", "peak_rss_mb", "runtime_s"])
        writer.writeheader()
        writer.writerows(results)

    # Group by size
    sizes = sorted(set(r["n"] for r in results))
    langs = sorted(set(r["language"] for r in results))

    with open(report_path, "w") as f:
        f.write("# Memory Profiling Report\n\n")
        f.write(f"Measured peak RSS (Resident Set Size) across {len(sizes)} graph sizes.\n\n")
        f.write(f"Platform: {platform.system()} {platform.machine()}\n\n")

        # Summary table
        f.write("## Peak Memory Usage (MB)\n\n")
        f.write(f"| Graph Size | " + " | ".join(langs) + " |\n")
        f.write(f"|---:|" + "|".join("---:" for _ in langs) + "|\n")

        for n in sizes:
            row = [f"n={n:,}"]
            for lang in langs:
                match = [r for r in results if r["language"] == lang and r["n"] == n]
                if match:
                    row.append(f"{match[0]['peak_rss_mb']:.2f}")
                else:
                    row.append("-")
            f.write("| " + " | ".join(row) + " |\n")

        f.write("\n## Runtime (seconds)\n\n")
        f.write(f"| Graph Size | " + " | ".join(langs) + " |\n")
        f.write(f"|---:|" + "|".join("---:" for _ in langs) + "|\n")

        for n in sizes:
            row = [f"n={n:,}"]
            for lang in langs:
                match = [r for r in results if r["language"] == lang and r["n"] == n]
                if match:
                    row.append(f"{match[0]['runtime_s']:.3f}")
                else:
                    row.append("-")
            f.write("| " + " | ".join(row) + " |\n")

        # Memory efficiency analysis
        f.write("\n## Memory Efficiency\n\n")
        f.write("Memory per vertex (KB) at largest tested graph size:\n\n")
        largest_n = max(sizes)
        for lang in langs:
            match = [r for r in results if r["language"] == lang and r["n"] == largest_n]
            if match:
                kb_per_vertex = (match[0]["peak_rss_mb"] * 1024) / largest_n
                f.write(f"- **{lang}**: {kb_per_vertex:.2f} KB/vertex\n")

        f.write(f"\n---\n\nGenerated by `benchmarks/memory_profile.py`\n")

    print(f"\n  Report: {report_path}")
    print(f"  CSV:    {csv_path}")


def cleanup_binaries(binaries):
    """Remove build artifacts."""
    for lang, path in binaries.items():
        if lang == "Java":
            continue
        if lang == "Go":
            p = Path(path)
            if p.exists():
                p.unlink()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Memory profiling for BMSSP implementations")
    parser.add_argument("--sizes", type=str, default=None,
                        help="Comma-separated graph sizes (default: 100,500,1000,5000,10000)")
    args = parser.parse_args()

    sizes = DEFAULT_SIZES
    if args.sizes:
        sizes = [int(s.strip()) for s in args.sizes.split(",")]

    print("Building implementations...")
    binaries = build_implementations()
    if not binaries:
        print("No implementations built successfully!", file=sys.stderr)
        return 1

    print(f"Built: {', '.join(binaries.keys())}")
    print(f"Graph sizes: {sizes}")

    results = run_memory_profile(binaries, sizes)
    if results:
        generate_report(results, binaries)

    cleanup_binaries(binaries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
