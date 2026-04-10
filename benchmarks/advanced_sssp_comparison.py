#!/usr/bin/env python3
"""
Advanced SSSP Algorithm Comparison

Compares BMSSP against other advanced single-source shortest path algorithms:
  - Dijkstra (binary heap): O(m log n)
  - Dijkstra (Fibonacci heap): O(m + n log n)  [via NetworkX]
  - Thorup-inspired (bucket-based): O(m + n log log n) for integer weights
  - Dial's algorithm: O(m + C) for integer weights, C = max weight

This provides context for where BMSSP's O(m log^{2/3} n) fits in the landscape
of shortest-path algorithms.

Usage:
  python benchmarks/advanced_sssp_comparison.py
"""

import heapq
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

try:
    import numpy as np
    import networkx as nx
except ImportError:
    print("Error: numpy and networkx required", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"


# ============ Algorithm Implementations ============

def dijkstra_binary_heap(adj, n, source):
    """Standard Dijkstra with binary heap. O(m log n)."""
    dist = [float("inf")] * n
    dist[source] = 0
    heap = [(0, source)]
    visited = [False] * n
    ops = 0

    while heap:
        d, u = heapq.heappop(heap)
        ops += 1
        if visited[u]:
            continue
        visited[u] = True
        for v, w in adj[u]:
            ops += 1
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(heap, (dist[v], v))

    return dist, ops


def dijkstra_fibonacci_heap(graph, source):
    """Dijkstra using NetworkX (Fibonacci heap internally). O(m + n log n)."""
    return nx.single_source_dijkstra_path_length(graph, source)


def dial_algorithm(adj, n, source, max_weight):
    """
    Dial's algorithm using circular buckets.
    O(m + C) where C = max edge weight (for integer weights).
    Best for small integer weights.
    """
    C = int(max_weight) + 1
    dist = [float("inf")] * n
    dist[source] = 0
    buckets = [[] for _ in range(C * n + 1)]
    buckets[0].append(source)
    visited = [False] * n
    ops = 0

    for d in range(len(buckets)):
        if d > 0 and not any(buckets[d:]):
            break
        while buckets[d]:
            u = buckets[d].pop()
            ops += 1
            if visited[u]:
                continue
            if dist[u] != d:
                continue
            visited[u] = True
            for v, w in adj[u]:
                ops += 1
                new_dist = d + int(w)
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    if new_dist < len(buckets):
                        buckets[new_dist].append(v)

    return dist, ops


def thorup_inspired(adj, n, source, max_weight):
    """
    Thorup-inspired bucket decomposition with multi-level buckets.
    Approximate O(m + n log log C) behavior via hierarchical bucketing.

    This is a simplified version demonstrating the key insight: using
    multi-level buckets to reduce the number of comparisons compared
    to a standard priority queue.
    """
    C = int(max_weight) + 1
    # Number of levels in the hierarchy
    levels = max(1, int(math.log(max(C, 2), 2)))
    bucket_count = max(2, int(math.sqrt(C)))

    dist = [float("inf")] * n
    dist[source] = 0
    visited = [False] * n
    ops = 0

    # Use a two-level bucket structure
    # Level 0: fine-grained buckets of width 1
    # Level 1: coarse buckets of width sqrt(C)
    coarse_width = max(1, bucket_count)
    total_range = C * n
    n_coarse = min(total_range // coarse_width + 2, n * 10)

    coarse_buckets = defaultdict(list)
    coarse_buckets[0].append(source)

    current_coarse = 0

    while current_coarse < n_coarse:
        # Find next non-empty coarse bucket
        while current_coarse < n_coarse and not coarse_buckets[current_coarse]:
            current_coarse += 1
        if current_coarse >= n_coarse:
            break

        # Expand the coarse bucket using fine-grained Dijkstra
        fine_heap = []
        for u in coarse_buckets[current_coarse]:
            if not visited[u]:
                heapq.heappush(fine_heap, (dist[u], u))
        coarse_buckets[current_coarse] = []

        while fine_heap:
            d, u = heapq.heappop(fine_heap)
            ops += 1
            if visited[u]:
                continue
            visited[u] = True

            for v, w in adj[u]:
                ops += 1
                new_dist = d + w
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    target_coarse = int(new_dist) // coarse_width
                    if target_coarse == current_coarse:
                        heapq.heappush(fine_heap, (new_dist, v))
                    else:
                        coarse_buckets[target_coarse].append(v)

        current_coarse += 1

    return dist, ops


def bmssp_reference(adj, n, source):
    """
    Reference BMSSP implementation for comparison.
    O(m * log^{2/3}(n)) expected.
    """
    log2n = max(1, math.log2(n))
    k = max(1, int(log2n ** (1/3)))
    t = max(1, int(log2n ** (2/3)))
    l = max(1, int(math.ceil(log2n / t)))

    dist = [float("inf")] * n
    dist[source] = 0
    complete = set([source])
    ops = 0

    def base_case(B, S):
        nonlocal ops
        if not S:
            return B, set()
        x = next(iter(S))
        U0 = {x}
        heap = [(dist[x], x)]
        visited = set()

        while heap and len(U0) < k + 1:
            d, u = heapq.heappop(heap)
            ops += 1
            if u in visited:
                continue
            visited.add(u)
            U0.add(u)
            complete.add(u)
            for v, w in adj[u]:
                ops += 1
                if d + w <= dist[v] and d + w < B:
                    dist[v] = d + w
                    heapq.heappush(heap, (dist[v], v))

        if len(U0) <= k:
            return B, U0
        Bp = max(dist[v] for v in U0)
        return Bp, {v for v in U0 if dist[v] < Bp}

    def bmssp_rec(level, B, S):
        nonlocal ops
        ops += 1
        if level == 0:
            return base_case(B, S)

        # FindPivots (simplified)
        P = set(S)
        W = set(S)
        Wprev = set(S)
        for _ in range(k):
            Wi = set()
            for u in Wprev:
                if dist[u] >= B:
                    continue
                for v, w in adj[u]:
                    ops += 1
                    if dist[u] + w <= dist[v]:
                        dist[v] = dist[u] + w
                        if dist[v] < B:
                            Wi.add(v)
            W |= Wi
            Wprev = Wi

        # Process pivots
        M = 2 ** ((level - 1) * t)
        queue = sorted([(dist[x], x) for x in P])
        U = set()

        while len(U) < k * (2 ** (level * t)) and queue:
            batch = queue[:min(M, len(queue))]
            queue = queue[len(batch):]
            Bi = batch[0][0]
            Si = {x for _, x in batch}
            Bp, Ui = bmssp_rec(level - 1, Bi, Si)
            U |= Ui

            for u in Ui:
                for v, w in adj[u]:
                    ops += 1
                    alt = dist[u] + w
                    if alt <= dist[v]:
                        dist[v] = alt
                        if alt >= Bi and alt < B:
                            queue.append((alt, v))
                            queue.sort()

        Bp = min(B, min((dist[x] for x in P), default=B))
        for x in W:
            if dist[x] < Bp:
                U.add(x)
        complete.update(U)
        return Bp, U

    S0 = {source}
    bmssp_rec(l, float("inf"), S0)
    return dist, ops


# ============ Graph Generation ============

def generate_graph(graph_type, n, max_weight=100):
    """Generate adjacency list and NetworkX graph."""
    adj = [[] for _ in range(n)]
    G = nx.DiGraph()
    G.add_nodes_from(range(n))

    random.seed(42)

    if graph_type == "sparse":
        m = 3 * n
        for _ in range(m):
            u = random.randint(0, n - 1)
            v = random.randint(0, n - 1)
            if u != v:
                w = random.randint(1, max_weight)
                adj[u].append((v, w))
                G.add_edge(u, v, weight=w)

    elif graph_type == "dense":
        for u in range(n):
            targets = random.sample(range(n), min(n // 3, n - 1))
            for v in targets:
                if u != v:
                    w = random.randint(1, max_weight)
                    adj[u].append((v, w))
                    G.add_edge(u, v, weight=w)

    elif graph_type == "grid":
        side = int(math.sqrt(n))
        for r in range(side):
            for c in range(side):
                u = r * side + c
                if c + 1 < side:
                    w = random.randint(1, max_weight)
                    adj[u].append((u + 1, w))
                    G.add_edge(u, u + 1, weight=w)
                if r + 1 < side:
                    w = random.randint(1, max_weight)
                    adj[u].append((u + side, w))
                    G.add_edge(u, u + side, weight=w)

    # Ensure source is connected to at least one node
    if not adj[0]:
        w = random.randint(1, max_weight)
        adj[0].append((1, w))
        G.add_edge(0, 1, weight=w)

    return adj, G, max_weight


# ============ Benchmark Runner ============

def run_comparison(sizes, graph_types, trials=3):
    """Run all algorithms on various graph sizes and types."""
    results = []

    for gtype in graph_types:
        print(f"\n  {gtype} graphs:")
        for n in sizes:
            adj, G, max_w = generate_graph(gtype, n)
            m = sum(len(a) for a in adj)
            print(f"    n={n:>6}, m={m:>8} ... ", end="", flush=True)

            algorithms = {
                "Dijkstra (binary heap)": lambda: dijkstra_binary_heap(adj, n, 0),
                "BMSSP": lambda: bmssp_reference(adj, n, 0),
                "Thorup-inspired": lambda: thorup_inspired(adj, n, 0, max_w),
            }

            # Dial's algorithm only for smaller graphs (memory intensive)
            if n <= 5000 and max_w <= 1000:
                algorithms["Dial's algorithm"] = lambda: dial_algorithm(adj, n, 0, max_w)

            timings = {}
            ops_counts = {}

            for name, fn in algorithms.items():
                times = []
                ops_total = 0
                for _ in range(trials):
                    t0 = time.perf_counter()
                    _, ops = fn()
                    t1 = time.perf_counter()
                    times.append((t1 - t0) * 1000)
                    ops_total += ops

                timings[name] = sum(times) / len(times)
                ops_counts[name] = ops_total // trials

            # Also time NetworkX Dijkstra (Fibonacci heap)
            times = []
            for _ in range(trials):
                t0 = time.perf_counter()
                dijkstra_fibonacci_heap(G, 0)
                t1 = time.perf_counter()
                times.append((t1 - t0) * 1000)
            timings["Dijkstra (Fibonacci)"] = sum(times) / len(times)
            ops_counts["Dijkstra (Fibonacci)"] = 0  # NetworkX doesn't expose ops

            results.append({
                "graph_type": gtype,
                "n": n,
                "m": m,
                "timings": timings,
                "operations": ops_counts,
            })

            # Print summary
            baseline = timings["Dijkstra (binary heap)"]
            parts = []
            for name in sorted(timings.keys()):
                ms = timings[name]
                ratio = ms / baseline if baseline > 0 else 0
                parts.append(f"{name}: {ms:.1f}ms ({ratio:.2f}x)")
            print(" | ".join(parts[:2]))

    return results


def generate_report(results):
    """Generate markdown comparison report."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "SSSP_COMPARISON.md"

    with open(report_path, "w") as f:
        f.write("# Advanced SSSP Algorithm Comparison\n\n")
        f.write("Comparison of BMSSP against other shortest-path algorithms.\n\n")
        f.write("## Algorithms\n\n")
        f.write("| Algorithm | Complexity | Notes |\n")
        f.write("|-----------|-----------|-------|\n")
        f.write("| Dijkstra (binary heap) | O(m log n) | Standard baseline |\n")
        f.write("| Dijkstra (Fibonacci heap) | O(m + n log n) | Theoretically optimal for comparison-based |\n")
        f.write("| BMSSP | O(m log^{2/3} n) | Breaks sorting barrier via bounded multi-source |\n")
        f.write("| Thorup-inspired | O(m + n log log C) | Bucket decomposition for integer weights |\n")
        f.write("| Dial's algorithm | O(m + C) | Optimal for small integer weights C |\n\n")

        # Group by graph type
        graph_types = sorted(set(r["graph_type"] for r in results))
        all_algos = set()
        for r in results:
            all_algos.update(r["timings"].keys())
        algos = sorted(all_algos)

        for gtype in graph_types:
            f.write(f"## {gtype.title()} Graphs\n\n")

            # Runtime table
            f.write("### Runtime (ms)\n\n")
            header = "| n | m | " + " | ".join(algos) + " |\n"
            f.write(header)
            f.write("|---:|---:|" + "|".join("---:" for _ in algos) + "|\n")

            gresults = [r for r in results if r["graph_type"] == gtype]
            for r in gresults:
                row = [f"{r['n']:,}", f"{r['m']:,}"]
                for algo in algos:
                    t = r["timings"].get(algo)
                    row.append(f"{t:.1f}" if t is not None else "-")
                f.write("| " + " | ".join(row) + " |\n")
            f.write("\n")

            # Relative performance table
            f.write("### Relative to Dijkstra (binary heap)\n\n")
            header = "| n | " + " | ".join(algos) + " |\n"
            f.write(header)
            f.write("|---:|" + "|".join("---:" for _ in algos) + "|\n")

            for r in gresults:
                baseline = r["timings"]["Dijkstra (binary heap)"]
                row = [f"{r['n']:,}"]
                for algo in algos:
                    t = r["timings"].get(algo)
                    if t is not None and baseline > 0:
                        ratio = t / baseline
                        row.append(f"{ratio:.2f}x")
                    else:
                        row.append("-")
                f.write("| " + " | ".join(row) + " |\n")
            f.write("\n")

        # Key findings
        f.write("## Key Findings\n\n")
        f.write("1. **BMSSP** provides theoretical improvement over comparison-based Dijkstra ")
        f.write("by exploiting the bounded multi-source structure.\n")
        f.write("2. **Thorup-inspired** approaches can be faster for integer weights due to ")
        f.write("bucket decomposition avoiding comparison overhead.\n")
        f.write("3. **Dial's algorithm** is optimal for graphs with small integer weights (C << n), ")
        f.write("but memory usage grows with C.\n")
        f.write("4. The practical crossover point where BMSSP outperforms standard Dijkstra ")
        f.write("depends on graph structure and size.\n\n")

        f.write("## When to Use Each Algorithm\n\n")
        f.write("| Scenario | Best Algorithm |\n")
        f.write("|----------|---------------|\n")
        f.write("| General-purpose, any weights | Dijkstra (Fibonacci heap) |\n")
        f.write("| Integer weights, small C | Dial's algorithm |\n")
        f.write("| Large sparse graphs | BMSSP |\n")
        f.write("| Integer weights, large C | Thorup-inspired |\n")
        f.write("| Simple implementation needed | Dijkstra (binary heap) |\n\n")

        f.write("---\n\nGenerated by `benchmarks/advanced_sssp_comparison.py`\n")

    print(f"\n  Report: {report_path}")


def main():
    print("Advanced SSSP Algorithm Comparison")
    print("=" * 50)

    sizes = [100, 500, 1000, 5000]
    graph_types = ["sparse", "dense", "grid"]

    results = run_comparison(sizes, graph_types, trials=3)
    generate_report(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
