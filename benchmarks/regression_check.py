#!/usr/bin/env python3
"""
Performance Regression Detection

Runs BMSSP and Dijkstra benchmarks for compiled implementations (C, Go, Rust),
compares against a stored baseline, and reports regressions.

Exit codes:
  0 - No regressions detected
  1 - Regressions detected (> threshold)
  2 - Baseline not found (first run, creates baseline)

Usage:
  python benchmarks/regression_check.py              # check against baseline
  python benchmarks/regression_check.py --update      # update baseline with current results
  python benchmarks/regression_check.py --threshold 20 # set regression threshold (%)
"""

import json
import os
import subprocess
import sys
import time
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = REPO_ROOT / "benchmarks" / "baseline.json"
HISTORY_DIR = REPO_ROOT / "benchmarks" / "history"
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"

DEFAULT_THRESHOLD = 15  # percentage
WARMUP_RUNS = 1
BENCH_RUNS = 5

# Graph sizes for regression benchmarks (smaller than full benchmark suite for speed)
GRAPH_SIZES = [100, 500, 1000]


def run_c_benchmarks():
    """Build and run C benchmarks, return timing dict."""
    impl_dir = REPO_ROOT / "implementations" / "c"
    # Build
    result = subprocess.run(
        ["gcc", "-Wall", "-Wextra", "-std=c11", "-O2", "benchmark.c", "-lm", "-o", "benchmark"],
        cwd=impl_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  C build failed: {result.stderr}", file=sys.stderr)
        return None

    # Run
    result = subprocess.run(
        ["./benchmark"], cwd=impl_dir, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        print(f"  C benchmark failed: {result.stderr}", file=sys.stderr)
        return None

    # Parse CSV output
    timings = {}
    for line in result.stdout.strip().split("\n"):
        if line.startswith("graph_type"):
            continue
        parts = line.split(",")
        if len(parts) == 5:
            graph_type, n, m, algo, time_ms = parts
            key = f"c/{graph_type}/n={n}/{algo}"
            timings[key] = float(time_ms)

    # Clean up
    bench_bin = impl_dir / "benchmark"
    if bench_bin.exists():
        bench_bin.unlink()

    return timings


def run_go_benchmarks():
    """Run Go benchmarks and parse output."""
    impl_dir = REPO_ROOT / "implementations" / "go"
    result = subprocess.run(
        ["go", "test", "-bench=BenchmarkRunSSSP", "-benchtime=3s", "-count=1", "-run=^$", "./..."],
        cwd=impl_dir, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        print(f"  Go benchmark failed: {result.stderr}", file=sys.stderr)
        return None

    timings = {}
    for line in result.stdout.strip().split("\n"):
        # Format: BenchmarkRunSSSP_Sparse_100-8   1234   987654 ns/op
        if line.startswith("Benchmark"):
            parts = line.split()
            if len(parts) >= 3 and "ns/op" in parts[-1]:
                name = parts[0]
                ns_op = float(parts[-2])
                timings[f"go/{name}"] = ns_op / 1e6  # convert to ms

    return timings


def run_rust_benchmarks():
    """Run Rust criterion benchmarks and parse output."""
    impl_dir = REPO_ROOT / "implementations" / "rust"
    result = subprocess.run(
        ["cargo", "bench", "--", "--output-format", "bencher"],
        cwd=impl_dir, capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        # Criterion may still output useful results even with non-zero exit
        if not result.stdout:
            print(f"  Rust benchmark failed: {result.stderr}", file=sys.stderr)
            return None

    timings = {}
    for line in result.stdout.strip().split("\n"):
        # Format: test bench_name ... bench: 1234 ns/iter (+/- 56)
        if "bench:" in line and "ns/iter" in line:
            parts = line.split()
            name = parts[1]
            bench_idx = parts.index("bench:")
            ns = float(parts[bench_idx + 1].replace(",", ""))
            timings[f"rust/{name}"] = ns / 1e6
        # Alternative Criterion format: name  time: [low est high]
        elif "time:" in line:
            parts = line.strip().split()
            if len(parts) >= 4:
                name = parts[0]
                # Try to extract the estimate value
                for i, p in enumerate(parts):
                    if p == "time:":
                        try:
                            # Criterion prints: time:   [1.2345 ms 1.3456 ms 1.4567 ms]
                            val_str = parts[i + 1].lstrip("[")
                            unit = parts[i + 2]
                            val = float(val_str)
                            if unit == "us" or unit.startswith("µ"):
                                val /= 1000
                            elif unit == "s":
                                val *= 1000
                            # Already ms
                            timings[f"rust/{name}"] = val
                        except (ValueError, IndexError):
                            pass

    return timings


def collect_benchmarks():
    """Run all benchmarks and return combined results."""
    print("Running benchmarks...")
    results = {}
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Get git info
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.strip()[:12]
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.strip()

    print("  Running C benchmarks...")
    c_results = run_c_benchmarks()
    if c_results:
        results.update(c_results)
        print(f"    collected {len(c_results)} data points")

    print("  Running Go benchmarks...")
    go_results = run_go_benchmarks()
    if go_results:
        results.update(go_results)
        print(f"    collected {len(go_results)} data points")

    print("  Running Rust benchmarks...")
    rust_results = run_rust_benchmarks()
    if rust_results:
        results.update(rust_results)
        print(f"    collected {len(rust_results)} data points")

    return {
        "timestamp": timestamp,
        "git_sha": sha,
        "git_branch": branch,
        "timings": results,
    }


def compare_to_baseline(current, baseline, threshold_pct):
    """Compare current results to baseline, return regressions."""
    regressions = []
    improvements = []
    unchanged = []

    for key, cur_ms in current["timings"].items():
        if key not in baseline["timings"]:
            continue
        base_ms = baseline["timings"][key]
        if base_ms <= 0:
            continue

        pct_change = ((cur_ms - base_ms) / base_ms) * 100

        entry = {
            "benchmark": key,
            "baseline_ms": round(base_ms, 3),
            "current_ms": round(cur_ms, 3),
            "change_pct": round(pct_change, 1),
        }

        if pct_change > threshold_pct:
            regressions.append(entry)
        elif pct_change < -threshold_pct:
            improvements.append(entry)
        else:
            unchanged.append(entry)

    return regressions, improvements, unchanged


def save_history(run_data):
    """Append run data to history."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{run_data['timestamp'].replace(':', '-')}_{run_data['git_sha']}.json"
    filepath = HISTORY_DIR / filename
    with open(filepath, "w") as f:
        json.dump(run_data, f, indent=2)
    print(f"  Saved to {filepath}")


def print_report(regressions, improvements, unchanged, current, baseline):
    """Print comparison report."""
    print("\n" + "=" * 70)
    print("PERFORMANCE REGRESSION REPORT")
    print("=" * 70)
    print(f"  Baseline: {baseline['git_sha']} ({baseline['timestamp']})")
    print(f"  Current:  {current['git_sha']} ({current['timestamp']})")
    print()

    if regressions:
        print(f"REGRESSIONS ({len(regressions)}):")
        print(f"  {'Benchmark':<45} {'Base':>8} {'Curr':>8} {'Change':>8}")
        print(f"  {'-'*45} {'-'*8} {'-'*8} {'-'*8}")
        for r in sorted(regressions, key=lambda x: -x["change_pct"]):
            print(
                f"  {r['benchmark']:<45} {r['baseline_ms']:>7.1f}ms {r['current_ms']:>7.1f}ms "
                f"+{r['change_pct']:>5.1f}%"
            )
        print()

    if improvements:
        print(f"IMPROVEMENTS ({len(improvements)}):")
        for r in sorted(improvements, key=lambda x: x["change_pct"]):
            print(
                f"  {r['benchmark']:<45} {r['baseline_ms']:>7.1f}ms {r['current_ms']:>7.1f}ms "
                f"{r['change_pct']:>5.1f}%"
            )
        print()

    n_total = len(regressions) + len(improvements) + len(unchanged)
    print(f"Summary: {len(regressions)} regressions, {len(improvements)} improvements, "
          f"{len(unchanged)} unchanged out of {n_total} benchmarks")
    print("=" * 70)


def generate_history_report():
    """Generate a markdown report from historical data."""
    if not HISTORY_DIR.exists():
        return

    history_files = sorted(HISTORY_DIR.glob("*.json"))
    if len(history_files) < 2:
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "HISTORY_REPORT.md"

    # Load all runs
    runs = []
    for f in history_files[-20:]:  # last 20 runs
        with open(f) as fh:
            runs.append(json.load(fh))

    # Find common benchmarks
    all_keys = set()
    for run in runs:
        all_keys.update(run["timings"].keys())

    with open(report_path, "w") as f:
        f.write("# Benchmark History\n\n")
        f.write(f"Last {len(runs)} runs\n\n")

        # Group by language
        for lang in ["c", "go", "rust"]:
            lang_keys = sorted(k for k in all_keys if k.startswith(f"{lang}/"))
            if not lang_keys:
                continue

            f.write(f"## {lang.upper()}\n\n")
            f.write(f"| Benchmark | " + " | ".join(
                r["git_sha"][:7] for r in runs
            ) + " |\n")
            f.write(f"|---|" + "|".join("---:" for _ in runs) + "|\n")

            for key in lang_keys:
                short_name = key.split("/", 1)[1]
                vals = []
                for run in runs:
                    v = run["timings"].get(key)
                    vals.append(f"{v:.1f}ms" if v is not None else "-")
                f.write(f"| {short_name} | " + " | ".join(vals) + " |\n")
            f.write("\n")

    print(f"  History report: {report_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Performance regression detection")
    parser.add_argument("--update", action="store_true", help="Update baseline with current results")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Regression threshold %% (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--history", action="store_true", help="Generate history report only")
    args = parser.parse_args()

    if args.history:
        generate_history_report()
        return 0

    current = collect_benchmarks()

    if not current["timings"]:
        print("No benchmark results collected!", file=sys.stderr)
        return 1

    # Save to history
    save_history(current)
    generate_history_report()

    if args.update or not BASELINE_FILE.exists():
        BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BASELINE_FILE, "w") as f:
            json.dump(current, f, indent=2)
        if args.update:
            print(f"\nBaseline updated: {BASELINE_FILE}")
        else:
            print(f"\nNo baseline found. Created initial baseline: {BASELINE_FILE}")
        return 2 if not args.update else 0

    # Load baseline
    with open(BASELINE_FILE) as f:
        baseline = json.load(f)

    regressions, improvements, unchanged = compare_to_baseline(
        current, baseline, args.threshold
    )
    print_report(regressions, improvements, unchanged, current, baseline)

    if regressions:
        print(f"\nFAILED: {len(regressions)} benchmark(s) regressed by more than {args.threshold}%")
        return 1

    print(f"\nPASSED: No regressions above {args.threshold}% threshold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
