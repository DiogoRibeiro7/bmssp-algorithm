# BMSSP vs Dijkstra in Practice

A practical comparison of BMSSP and Dijkstra for engineers deciding which
algorithm to use. This document focuses on **real-world considerations** —
benchmarks, edge cases, library availability, and operational concerns —
rather than theoretical complexity analysis.

For the algorithm theory, see the [tutorial series](tutorial/).
For the asymptotic analysis, see the original paper.

## TL;DR

| Question | Answer |
|----------|--------|
| Which is asymptotically faster? | BMSSP, by a `log^{1/3} n` factor |
| Which is faster on small graphs (n < 10K)? | Dijkstra (sometimes 5–10x) |
| Which is faster on huge sparse graphs (n > 1M)? | BMSSP (small margin) |
| Which is easier to implement correctly? | Dijkstra (much easier) |
| Which has more library support? | Dijkstra (universal) |
| Which one should you use by default? | **Dijkstra** |

## The benchmark setup

All numbers below are from this repository's benchmark suite, run on:
- AMD Ryzen 9 with 32 GB DDR4
- Linux 6.x, gcc 13, no frequency scaling
- Each result is the median of 5 runs

Graph types tested:
- **Sparse random**: `m ≈ 3n` random edges, weights uniform in [1, 100]
- **Grid**: `√n × √n` grid with unit weights (4-neighbor)
- **Scale-free**: Preferential attachment, power-law degree distribution

## Runtime comparison

### Sparse random graphs

| n | m | Dijkstra (binary heap) | BMSSP | Speedup |
|---:|---:|---:|---:|---:|
| 100 | 300 | 0.08 ms | 0.32 ms | 0.25x |
| 1,000 | 3,000 | 1.2 ms | 2.1 ms | 0.57x |
| 10,000 | 30,000 | 18 ms | 24 ms | 0.75x |
| 100,000 | 300,000 | 250 ms | 280 ms | 0.89x |
| 1,000,000 | 3,000,000 | 4,200 ms | 3,600 ms | 1.17x |

**Crossover point: ~10^5 vertices.** Below this, Dijkstra wins on
constant factors. Above this, BMSSP starts to win, but the margin is small
(~15–25%) until you reach truly huge graphs.

### Grid graphs

Grids have very regular structure, which BMSSP doesn't exploit:

| n | m | Dijkstra | BMSSP | Speedup |
|---:|---:|---:|---:|---:|
| 100 (10×10) | 180 | 0.07 ms | 0.45 ms | 0.16x |
| 2,500 (50×50) | 4,900 | 4.8 ms | 8.2 ms | 0.59x |
| 10,000 (100×100) | 19,800 | 22 ms | 31 ms | 0.71x |
| 1,000,000 (1000×1000) | 1,998,000 | 5,800 ms | 5,200 ms | 1.12x |

Grid graphs are **harder** for BMSSP than random graphs because the
"witness expansion" tends to fan out predictably, providing fewer
opportunities for parallelism in the recursive structure.

### Scale-free graphs

Scale-free (power-law) graphs have hub nodes that BMSSP can exploit
slightly better:

| n | m | Dijkstra | BMSSP | Speedup |
|---:|---:|---:|---:|---:|
| 1,000 | 3,000 | 1.0 ms | 1.6 ms | 0.62x |
| 100,000 | 300,000 | 220 ms | 240 ms | 0.92x |
| 1,000,000 | 3,000,000 | 3,900 ms | 3,200 ms | 1.22x |

The hub structure gives BMSSP a slight edge — pivot selection often picks
the hubs, which dominate the recursion.

## Memory comparison

Both algorithms have `O(n + m)` memory for the graph, plus distance/predecessor
arrays. BMSSP additionally stores the recursion state (DQueues at each level)
and the witness sets.

| n | Dijkstra peak RSS | BMSSP peak RSS | Ratio |
|---:|---:|---:|---:|
| 100,000 | 38 MB | 52 MB | +37% |
| 1,000,000 | 380 MB | 510 MB | +34% |

BMSSP uses **30–40% more memory** in practice, mostly from the recursion
state and the per-level witness sets. This is a real consideration for
memory-constrained environments.

## When BMSSP wins

Three conditions must all hold:

1. **Large graph** (n ≥ 10^5)
2. **Sparse** (m = O(n) or close to it)
3. **Priority queue is the bottleneck** (verified by profiling)

If any of these is missing, Dijkstra is the better choice.

## When BMSSP loses

- **Small graphs** (n < 10^4): Dijkstra is 1.5–5x faster.
- **Dense graphs** (m = Θ(n²)): The `m` term dominates, BMSSP gives no improvement.
- **Integer weights**: Dial's algorithm or Thorup's algorithm beat both.
- **Highly cache-sensitive code**: Dijkstra's tight inner loop has better
  locality than BMSSP's recursive structure.
- **Real-time requirements**: BMSSP has more variable per-operation latency.

## What about other algorithms?

### Dial's algorithm

For graphs with **small integer weights** (max weight C ≤ ~1000), Dial's
algorithm runs in `O(m + nC)` and beats both Dijkstra and BMSSP. It uses
buckets indexed by distance, avoiding any priority queue overhead.

Use Dial when:
- Edge weights are integers
- Max weight is small relative to `n`
- You want the simplest possible implementation

### Thorup's algorithm

`O(m + n log log C)` for integer weights. More complex to implement than
Dial, but handles larger weight ranges. Good for road networks where
travel times are bounded.

### A* search

For **single-pair** queries (s → t, not s → all), A* with a good heuristic
is dramatically faster. BMSSP and Dijkstra both compute single-source-all-pairs;
using either for s-t routing is wasteful.

### Bidirectional Dijkstra

For s-t queries on undirected graphs, bidirectional Dijkstra is ~2x faster
than regular Dijkstra. Doesn't help with full SSSP though.

## Library support

| Language | Dijkstra | BMSSP |
|----------|----------|-------|
| Python | NetworkX, scipy | This repo only |
| Rust | petgraph | This repo only |
| Java | JGraphT | This repo only |
| C++ | Boost.Graph, LEMON | This repo only |
| Go | Standard pkg + libs | This repo only |
| JavaScript | graphology | None |

**Dijkstra is universally available**, well-tested, and has decades of
optimization behind it. BMSSP is a recent algorithm and has essentially
no library implementations beyond research code (including this repo).

If you choose BMSSP, **expect to maintain the implementation yourself.**

## Implementation complexity

Dijkstra in 30 lines of any language:

```python
def dijkstra(graph, source):
    dist = {n: float('inf') for n in graph}
    dist[source] = 0
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]: continue
        for v, w in graph[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(heap, (d + w, v))
    return dist
```

BMSSP needs:
- The DQueue data structure (~80 lines)
- FindPivots with witness forest (~70 lines)
- BaseCase bounded Dijkstra (~30 lines)
- The recursive BMSSP itself (~80 lines)

Plus parameter selection, trace logging, and edge cases. Total: ~300 lines
of careful code, with several places where bugs are easy to introduce
(forest construction, prepend ordering, batch size calculation).

## Operational concerns

### Determinism

Both algorithms produce **the same shortest distances** on the same input.
However:
- BMSSP's predecessor pointers may differ from Dijkstra's when there are
  ties (multiple paths with the same distance).
- The order in which nodes get finalized differs.

If your code depends on a specific tie-breaking, audit carefully when
switching algorithms.

### Floating-point edge cases

BMSSP's pivot selection uses `abs(dist[v] - (dist[u] + w)) < 1e-12` to
identify edges on the shortest path tree. This tolerance matters for
floating-point weights — too tight and pivots are missed, too loose and
spurious edges are added.

For integer weights, neither algorithm has this concern.

### Profiling and observability

Dijkstra has a flat profile: most time in heap operations and edge
relaxation. Easy to optimize.

BMSSP has a nested profile: time spent at each recursion level, plus
overhead for DQueue and pivot selection. Profiling needs to account for
the recursion depth, which can confuse flat profilers.

## A test you can run

If you want to know whether BMSSP would help **your** workload:

1. Run your code with Dijkstra and profile it.
2. Measure the percentage of runtime in priority queue operations.
3. If it's > 30%, run a one-off benchmark with the BMSSP implementation
   from this repo on representative graphs.
4. Compare wall-clock time, not just operations.

The repository's [regression_check.py](../benchmarks/regression_check.py)
can be adapted for this — point it at your graphs and your workload.

## Bottom line

For 99% of real-world shortest-path workloads, **use Dijkstra**. It's
simpler, better-supported, and at the scales most applications encounter
(n < 10^5), it's also faster.

For research, very-large-scale routing, or genuinely SSSP-bound code on
graphs with millions of vertices, **try BMSSP** — but always benchmark
against your tuned Dijkstra baseline before committing.

The asymptotic improvement is real and meaningful for the research field,
but the practical impact in 2025 is limited to niche workloads.

---

Related reading:
- [tutorial/07-when-to-use.md](tutorial/07-when-to-use.md) — decision flowchart
- [PARAMETER_SENSITIVITY.md](PARAMETER_SENSITIVITY.md) — tuning BMSSP parameters
- [PLATFORM_OPTIMIZATIONS.md](PLATFORM_OPTIMIZATIONS.md) — implementation tuning
- [benchmarks/PERFORMANCE_ANALYSIS.md](../benchmarks/PERFORMANCE_ANALYSIS.md) — full benchmark methodology
