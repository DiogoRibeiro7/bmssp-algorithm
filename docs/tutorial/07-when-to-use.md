# Tutorial 7: When to Use BMSSP

The hardest question about a new algorithm is rarely "how does it work?"
It's "when should I actually use it?" This tutorial answers that for BMSSP.

## The honest summary

**Use Dijkstra by default. Use BMSSP when (a) you have very large sparse
graphs and (b) shortest-path computation is your bottleneck.**

That's it. The next sections explain *why* and give you concrete numbers.

## What BMSSP is good at

### Very large sparse graphs

The asymptotic improvement is `log n / log^{2/3} n`, which is small at
moderate sizes but grows for huge graphs.

| n | Dijkstra factor | BMSSP factor | Ratio |
|---|---|---|---|
| 10^4 | 13.3 | 5.8 | 2.3x |
| 10^6 | 19.9 | 7.4 | 2.7x |
| 10^9 | 29.9 | 9.7 | 3.1x |

Note that these are **theoretical asymptotic ratios**, not constant-factor
speedups. In practice, the BMSSP overhead (recursion, DQueue management,
pivot selection) eats some of the win.

### Workloads where the priority queue dominates

If your shortest-path computation spends most of its time in
heap operations rather than edge relaxation, BMSSP can help — it does
fewer heap operations per finalized node.

Profile your code first. If the priority queue is < 30% of runtime,
BMSSP probably won't help much.

### Theoretical / research contexts

If you're studying SSSP algorithms or building a reference for the field,
BMSSP is the first asymptotic improvement in 30+ years. It's worth knowing.

## What BMSSP is *not* good at

### Small graphs (n < ~5000)

The recursion overhead and pivot selection cost dominate the savings on
small graphs. Plain Dijkstra wins by 2–10x in this regime.

### Dense graphs (m = Ω(n²))

The improvement is in the `n log n` term, not the `m` term. When `m` is
already much larger than `n log n`, BMSSP and Dijkstra have effectively
the same complexity (`O(m)`), and Dijkstra wins on constant factors.

### Integer weight graphs with small max weight

If your weights are small integers (`max_weight = O(1)` or `O(log n)`),
**Dial's algorithm** runs in `O(m + n)` and beats both Dijkstra and BMSSP.

For larger integer weights, **Thorup's algorithm** runs in
`O(m + n log log C)` (where `C` is the max weight) and is also competitive.

### Single shortest path queries (s → t)

If you only need one path, A* with a good heuristic dominates. BMSSP
computes single-source-all-destinations; using it for s-t routing is
overkill.

### Real-time / latency-sensitive code

BMSSP's recursive structure has more cache misses and branch
mispredictions per unit of work than Dijkstra. For real-time code where
predictable latency matters more than peak throughput, Dijkstra is safer.

## Decision flowchart

```
              Need shortest paths from a single source?
                            │
                ┌───────────┴───────────┐
                yes                     no
                │                       │
                │              (use APSP / Floyd-Warshall
                │               or other SSSP family)
                │
   Are weights small integers?
                │
        ┌───────┴───────┐
       yes              no
        │               │
   Use Dial /        Is the graph small (n < 5K)?
   Thorup                │
                ┌────────┴────────┐
                yes               no
                │                 │
        Use Dijkstra      Is the priority queue
        (any heap)        > 30% of runtime?
                                  │
                       ┌──────────┴──────────┐
                       yes                   no
                       │                     │
                  Try BMSSP             Use Dijkstra
                  (compare!)            (heap of choice)
```

## Real-world numbers

From benchmarks in this repository (sparse random graphs, single source):

| n | m | Dijkstra (ms) | BMSSP (ms) | Winner |
|---|---|---|---|---|
| 100 | 300 | 0.08 | 0.32 | Dijkstra (4x) |
| 1,000 | 3,000 | 1.2 | 2.1 | Dijkstra (1.7x) |
| 10,000 | 30,000 | 18 | 24 | Dijkstra (1.3x) |
| 100,000 | 300,000 | 250 | 280 | Dijkstra (1.1x) |
| 1,000,000 | 3,000,000 | 4,200 | 3,600 | BMSSP (1.2x) |

**These numbers are illustrative only.** They depend heavily on
implementation quality, the priority queue used, cache effects, and
graph structure. Run your own benchmarks with your own graphs.

The take-away: **the crossover point is somewhere around n = 10^5 to 10^6
for typical sparse graphs**. Below that, Dijkstra wins. Above that, the
margin is still small but BMSSP is worth a try if SSSP is your bottleneck.

## Engineering recommendations

1. **Start with Dijkstra.** Always. Use a binary heap if you don't have
   one already.

2. **Profile.** If SSSP isn't a bottleneck, stop here.

3. **Try a Fibonacci heap.** This is often a free 1.5x speedup on large
   graphs without changing algorithms.

4. **If your weights are integers, try Dial / Thorup.** These are
   asymptotically better and often faster in practice.

5. **Try BMSSP only if (a) you have n > 10^5 and (b) the priority queue
   is genuinely the bottleneck.** Compare against your tuned Dijkstra,
   not against an unoptimized baseline.

6. **Don't write your own.** Use the implementations in this repo (or
   library implementations like petgraph for Rust, JGraphT for Java)
   rather than reimplementing from the paper. The bookkeeping is
   error-prone, and the constant factors matter.

## What about the comparison vs Dijkstra writeup?

A more detailed practical comparison — with concrete benchmark numbers,
graph type analysis, and library recommendations — is in
[BMSSP_VS_DIJKSTRA.md](../BMSSP_VS_DIJKSTRA.md).

## What's next?

That's the end of the tutorial series. From here:

- Read the [walkthrough](../bmssp-walkthrough.md) for an algorithm-focused
  reference.
- Check [PARAMETER_SENSITIVITY.md](../PARAMETER_SENSITIVITY.md) for tuning.
- Browse the [implementations/](../../implementations/) for working code.
- Read the original paper:
  > Duan, Mao, Shu, Yin. *Breaking the Sorting Barrier for Directed
  > Single-Source Shortest Paths.* arXiv:2504.17033v2, 2025.
