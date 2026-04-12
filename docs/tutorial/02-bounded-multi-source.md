# Tutorial 2: Bounded Multi-Source Search

## The shape of the new primitive

Instead of computing single-source shortest paths in one shot, BMSSP relies
on a more flexible primitive:

**Given a *set* of source nodes `S` and a *distance bound* `B`, compute
shortest distances to all reachable nodes within `B`.**

Two things distinguish this from plain Dijkstra:

1. **Multiple sources at once.** Each source `s ∈ S` already has a tentative
   distance (it might be in the middle of the graph, not at the boundary).
   The algorithm computes shortest paths from all of them in parallel.
2. **Bounded.** Anything with distance `≥ B` is ignored. This is the key
   knob — by choosing `B` carefully, we can finalize many nodes at once
   without paying the full Dijkstra sort cost.

## A toy example

Suppose you've already finalized:

```
s ----> a (dist=1)    s -- 4 --> b
 \       \1
  \       v
   4      b (dist=3, NOT yet finalized)
```

You know `dist[s] = 0` and `dist[a] = 1`. The next step in standard Dijkstra
would be to extract `b` with `dist=3`, finalize it, then extract `c` with
`dist=4`, etc.

In **bounded multi-source** search, you say instead: "give me everything
reachable from `{s, a}` within distance bound 5". The result is the set
`{s, a, b, c}` with their final distances — all in one call.

The point: **you finalize 4 nodes in one batch**, where Dijkstra would have
done 4 sequential extractions.

## Why does this break the sorting barrier?

Each batch of finalizations processes `k` nodes. The work per batch is
roughly proportional to the number of edges leaving those nodes — call it
`m_batch`. Across all batches:

$$\sum_{\text{batches}} m_{\text{batch}} = m$$

So the total work is `O(m + Q)` where `Q` is the cost of managing the queue
between batches. If `Q << n log n` (because we don't sort all `n` nodes),
we win.

The trick is that **batches don't need to be sorted internally**. We only
need to know that the batch is complete (no node outside the batch can
have a smaller distance than any node inside). The hierarchical bucket
structure of BMSSP guarantees this property without paying for a full sort.

## What does "bounded" enable?

Three things, all critical:

1. **Pruning.** Edges leading to nodes with distance `≥ B` are skipped.
2. **Termination.** The algorithm stops as soon as it can't improve any
   distance below `B`. This bounds the work for each call.
3. **Composition.** A bounded call with bound `B` can be decomposed into
   sub-calls with smaller bounds `B_1 < B_2 < ... < B`, processed in order.
   Each sub-call finalizes a subset.

This last property is what makes the recursion work — and the recursion is
where the `log^{2/3} n` factor comes from.

## A first sketch

Here's the shape of the bounded multi-source primitive (we'll refine this
in later tutorials):

```
function BoundedSSSP(S, B):
    Q := priority queue, seeded with (s, dist[s]) for s in S
    while Q is not empty:
        (u, d) := Q.pop_min()
        if d >= B: break
        if u is already finalized: continue
        finalize u
        for each edge (u, v, w):
            if d + w < dist[v]:
                dist[v] = d + w
                Q.push(v, d + w)
```

This is **just bounded Dijkstra**. It already gives O((m + n) log n) bounded
to within `B`. The advance comes from the fact that we'll wrap this primitive
in a recursive structure that picks `B` cleverly and reuses work across
recursion levels.

## What's next?

In [Tutorial 3](03-dqueue.md), we'll look at the **DQueue** — the data
structure that makes the bounded primitive efficient. It's a small but
clever variation on a standard priority queue, called out in the paper as
Lemma 3.3.
