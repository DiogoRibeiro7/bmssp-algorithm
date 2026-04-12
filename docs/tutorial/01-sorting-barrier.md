# Tutorial 1: The Sorting Barrier

## What is the "sorting barrier"?

When you compute single-source shortest paths (SSSP) on a directed graph with
positive edge weights, the textbook algorithm is **Dijkstra**. Its complexity
depends on the priority queue you use:

| Priority queue | Time complexity |
|----------------|-----------------|
| Binary heap | O((m + n) log n) |
| Fibonacci heap | O(m + n log n) |
| Bucket / radix (integer weights) | O(m + n log log n) |

For decades, the **best comparison-based bound was O(m + n log n)** with
Fibonacci heaps. The `n log n` term is fundamentally a *sorting cost*: every
distance has to be extracted from the priority queue in sorted order.

This is the "sorting barrier": **if your algorithm finalizes nodes in
distance order, you pay a sorting cost.**

## Why does Dijkstra need to sort?

Dijkstra's correctness rests on a single invariant: **the next node to
finalize is the one with the smallest tentative distance.** That node's
distance can never improve (because all edges have non-negative weight),
so it can be marked complete.

The implication: at every step, you need the *minimum* of the unfinalized
distances. Over `n` finalizations, this is `n` minimum-extractions, and any
data structure that supports both insertion and minimum-extraction in
better than O(log n) per operation runs into well-known lower bounds.

## What if we don't finalize one node at a time?

The BMSSP insight is to **finalize nodes in batches**, accepting that some
nodes might be discovered with non-optimal distances initially and revisited
later. Specifically:

1. Pick a *bound* `B`. Anything with distance `≥ B` is deferred.
2. Inside the bound, finalize a **set** of nodes (a small "batch" of pivots).
3. Recurse on smaller bounds.

The key trick: by working with bounded multi-source subproblems, the algorithm
doesn't need a strict total order over all nodes. It only needs a partial
order, and that's enough to break the sorting barrier.

## The new bound

BMSSP achieves:

$$O\left(m \cdot \log^{2/3} n\right)$$

This is asymptotically faster than O(m + n log n) when `m = O(n)` (sparse
graphs). The improvement comes from replacing the full sort with a
hierarchical bucket decomposition.

| n | log n | log^{2/3} n | Speedup ratio |
|---|-------|-------------|----------------|
| 10^3 | ~10 | ~4.6 | ~2.2x |
| 10^6 | ~20 | ~7.4 | ~2.7x |
| 10^9 | ~30 | ~9.7 | ~3.1x |

The speedup grows logarithmically — small but real, and it's the **first
asymptotic improvement** for general SSSP in over 30 years.

## What you can't expect

- BMSSP is **not** a constant-factor optimization. On small graphs (n < 1000),
  the bookkeeping overhead is larger than the savings, and Dijkstra wins.
- BMSSP **doesn't change** the lower bound for *non-comparison* settings.
  If your weights are small integers, Dial's algorithm or radix heaps still
  beat BMSSP.
- BMSSP **doesn't help** dense graphs (m = Ω(n²)), where the n log n term
  is dominated by m anyway.

## What's next?

In [Tutorial 2](02-bounded-multi-source.md) we'll look at the core insight:
*bounded multi-source search*, and why it's the right primitive for breaking
the sorting barrier.
