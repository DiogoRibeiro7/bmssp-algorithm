#!/usr/bin/env python3
"""
Large-Graph Benchmarks (n > 10^6)

Tests compiled BMSSP implementations on graphs with millions of vertices.
Only uses compiled implementations (C, Go, Rust) since Python/Java are
too slow at this scale.

Generates sparse random and grid graphs, writes them as DOT files,
and measures wall-clock runtime and peak memory.

Usage:
  python benchmarks/large_graph_bench.py
  python benchmarks/large_graph_bench.py --sizes 100000,500000,1000000
  python benchmarks/large_graph_bench.py --only c,rust
"""

import csv
import math
import os
import platform
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"

DEFAULT_SIZES = [10_000, 100_000, 500_000, 1_000_000, 2_000_000]


def generate_large_dot(n, edge_factor=3, seed=42, path=None):
    """
    Generate a large sparse DOT graph efficiently, writing directly to file.
    Returns the path and edge count.
    """
    rng = random.Random(seed)

    if path is None:
        fd, path = tempfile.mkstemp(suffix=".dot")
        os.close(fd)

    m = 0
    with open(path, "w") as f:
        f.write("digraph G {\n")

        # Ensure connectivity: chain through first sqrt(n) nodes
        chain_len = min(int(math.sqrt(n)), n - 1)
        for i in range(chain_len):
            w = rng.randint(1, 100)
            f.write(f"  n{i} -> n{i+1} [label={w}];\n")
            m += 1

        # Random edges
        target_m = edge_factor * n
        for _ in range(target_m):
            u = rng.randint(0, n - 1)
            v = rng.randint(0, n - 1)
            if u != v:
                w = rng.randint(1, 100)
                f.write(f"  n{u} -> n{v} [label={w}];\n")
                m += 1

        f.write("}\n")

    return path, m


def generate_large_grid_dot(side, path=None):
    """Generate a grid DOT graph with side x side nodes."""
    if path is None:
        fd, path = tempfile.mkstemp(suffix=".dot")
        os.close(fd)

    n = side * side
    m = 0
    with open(path, "w") as f:
        f.write("digraph G {\n")
        for r in range(side):
            for c in range(side):
                u = r * side + c
                if c + 1 < side:
                    f.write(f"  n{u} -> n{u+1} [label=1];\n")
                    m += 1
                if r + 1 < side:
                    f.write(f"  n{u} -> n{u+side} [label=1];\n")
                    m += 1
        f.write("}\n")

    return path, n, m


def build_implementations(only=None):
    """Build compiled implementations."""
    binaries = {}
    impl_dir = REPO_ROOT / "implementations"
    ext = ".exe" if platform.system() == "Windows" else ""

    targets = {
        "c": {
            "dir": impl_dir / "c",
            "build": ["gcc", "-std=c11", "-O2", "bmssp.c", "-lm", "-o", f"bmssp{ext}"],
            "bin": f"bmssp{ext}",
        },
        "go": {
            "dir": impl_dir / "go",
            "build": ["go", "build", "-ldflags=-s -w", "-o", f"bmssp_large{ext}", "./cmd/bmssp/"],
            "bin": f"bmssp_large{ext}",
        },
        "rust": {
            "dir": impl_dir / "rust",
            "build": ["cargo", "build", "--release"],
            "bin": os.path.join("target", "release", f"bmssp{ext}"),
        },
    }

    if only:
        targets = {k: v for k, v in targets.items() if k in only}

    for lang, cfg in targets.items():
        print(f"  Building {lang}...", end=" ", flush=True)
        result = subprocess.run(
            cfg["build"], cwd=cfg["dir"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            binaries[lang] = str(cfg["dir"] / cfg["bin"])
            print("ok")
        else:
            print(f"FAILED: {result.stderr[:200]}")

    return binaries


def measure_run(binary, dot_path, source="n0"):
    """Run a binary and measure wall-clock time and peak RSS."""
    cmd = [binary, dot_path, source]

    start = time.monotonic()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    peak_rss = 0
    if psutil:
        try:
            ps = psutil.Process(proc.pid)
            while proc.poll() is None:
                try:
                    mem = ps.memory_info()
                    peak_rss = max(peak_rss, mem.rss)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
                time.sleep(0.05)
        except psutil.NoSuchProcess:
            pass

    proc.wait(timeout=600)
    elapsed = time.monotonic() - start

    if proc.returncode != 0:
        stderr = proc.stderr.read().decode()[:300]
        return None, None, stderr

    return elapsed, peak_rss / (1024 * 1024) if peak_rss else None, None


def run_benchmarks(binaries, sizes):
    """Run large-graph benchmarks."""
    results = []

    for n in sizes:
        print(f"\n  === Sparse graph n={n:,} ===")

        # Generate graph
        t0 = time.monotonic()
        dot_path, m = generate_large_dot(n, edge_factor=3)
        gen_time = time.monotonic() - t0
        dot_size_mb = os.path.getsize(dot_path) / (1024 * 1024)
        print(f"    Generated: {m:,} edges, {dot_size_mb:.1f} MB DOT file in {gen_time:.1f}s")

        for lang, binary in sorted(binaries.items()):
            print(f"    {lang:>6}: ", end="", flush=True)
            elapsed, rss_mb, err = measure_run(binary, dot_path)

            if elapsed is not None:
                results.append({
                    "graph_type": "sparse",
                    "n": n,
                    "m": m,
                    "language": lang,
                    "time_s": round(elapsed, 3),
                    "peak_rss_mb": round(rss_mb, 1) if rss_mb else None,
                })
                rss_str = f", RSS: {rss_mb:.1f} MB" if rss_mb else ""
                print(f"{elapsed:.3f}s{rss_str}")
            else:
                print(f"FAILED: {err}")

        os.unlink(dot_path)

        # Grid benchmarks (only up to ~1M since grid n = side^2)
        side = int(math.sqrt(n))
        if side * side <= 2_000_000:
            print(f"\n  === Grid graph {side}x{side} (n={side*side:,}) ===")

            t0 = time.monotonic()
            dot_path, grid_n, grid_m = generate_large_grid_dot(side)
            gen_time = time.monotonic() - t0
            dot_size_mb = os.path.getsize(dot_path) / (1024 * 1024)
            print(f"    Generated: {grid_m:,} edges, {dot_size_mb:.1f} MB in {gen_time:.1f}s")

            for lang, binary in sorted(binaries.items()):
                print(f"    {lang:>6}: ", end="", flush=True)
                elapsed, rss_mb, err = measure_run(binary, dot_path)

                if elapsed is not None:
                    results.append({
                        "graph_type": "grid",
                        "n": grid_n,
                        "m": grid_m,
                        "language": lang,
                        "time_s": round(elapsed, 3),
                        "peak_rss_mb": round(rss_mb, 1) if rss_mb else None,
                    })
                    rss_str = f", RSS: {rss_mb:.1f} MB" if rss_mb else ""
                    print(f"{elapsed:.3f}s{rss_str}")
                else:
                    print(f"FAILED: {err}")

            os.unlink(dot_path)

    return results


def generate_report(results):
    """Generate markdown report for large-graph benchmarks."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "LARGE_GRAPH_REPORT.md"
    csv_path = RESULTS_DIR / "large_graph_results.csv"

    # Save CSV
    if results:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    langs = sorted(set(r["language"] for r in results))

    with open(report_path, "w") as f:
        f.write("# Large-Graph Benchmark Results\n\n")
        f.write("Testing BMSSP implementations on graphs with n > 10,000 vertices.\n\n")
        f.write(f"Platform: {platform.system()} {platform.machine()}\n\n")

        for gtype in ["sparse", "grid"]:
            gresults = [r for r in results if r["graph_type"] == gtype]
            if not gresults:
                continue

            f.write(f"## {gtype.title()} Graphs\n\n")

            # Runtime table
            f.write("### Runtime (seconds)\n\n")
            f.write("| n | m | " + " | ".join(langs) + " |\n")
            f.write("|---:|---:|" + "|".join("---:" for _ in langs) + "|\n")

            sizes = sorted(set(r["n"] for r in gresults))
            for n in sizes:
                m_val = next((r["m"] for r in gresults if r["n"] == n), 0)
                row = [f"{n:,}", f"{m_val:,}"]
                for lang in langs:
                    match = [r for r in gresults if r["n"] == n and r["language"] == lang]
                    if match:
                        row.append(f"{match[0]['time_s']:.3f}")
                    else:
                        row.append("-")
                f.write("| " + " | ".join(row) + " |\n")
            f.write("\n")

            # Memory table
            has_memory = any(r["peak_rss_mb"] for r in gresults)
            if has_memory:
                f.write("### Peak Memory (MB)\n\n")
                f.write("| n | " + " | ".join(langs) + " |\n")
                f.write("|---:|" + "|".join("---:" for _ in langs) + "|\n")

                for n in sizes:
                    row = [f"{n:,}"]
                    for lang in langs:
                        match = [r for r in gresults if r["n"] == n and r["language"] == lang]
                        if match and match[0]["peak_rss_mb"]:
                            row.append(f"{match[0]['peak_rss_mb']:.1f}")
                        else:
                            row.append("-")
                    f.write("| " + " | ".join(row) + " |\n")
                f.write("\n")

        # Scaling analysis
        f.write("## Scaling Analysis\n\n")
        f.write("Throughput (vertices/second) at the largest tested size:\n\n")
        max_n = max(r["n"] for r in results)
        for lang in langs:
            match = [r for r in results if r["language"] == lang and r["n"] == max_n]
            if match:
                throughput = max_n / match[0]["time_s"]
                f.write(f"- **{lang.upper()}**: {throughput:,.0f} vertices/sec\n")
        f.write("\n")

        f.write("---\n\nGenerated by `benchmarks/large_graph_bench.py`\n")

    print(f"\n  Report: {report_path}")
    print(f"  CSV:    {csv_path}")


def cleanup(binaries):
    """Remove build artifacts."""
    for lang, path in binaries.items():
        if lang == "go":
            p = Path(path)
            if p.exists():
                p.unlink()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Large-graph benchmarks")
    parser.add_argument("--sizes", type=str, default=None,
                        help="Comma-separated graph sizes")
    parser.add_argument("--only", type=str, default=None,
                        help="Comma-separated languages (c,go,rust)")
    args = parser.parse_args()

    sizes = DEFAULT_SIZES
    if args.sizes:
        sizes = [int(s.strip()) for s in args.sizes.split(",")]

    only = None
    if args.only:
        only = [s.strip().lower() for s in args.only.split(",")]

    print("Large-Graph Benchmarks")
    print("=" * 50)
    print(f"Sizes: {[f'{s:,}' for s in sizes]}")

    print("\nBuilding implementations...")
    binaries = build_implementations(only)
    if not binaries:
        print("No implementations built!", file=sys.stderr)
        return 1

    print(f"Available: {', '.join(binaries.keys())}")

    results = run_benchmarks(binaries, sizes)
    if results:
        generate_report(results)

    cleanup(binaries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
