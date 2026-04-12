# Tutorial 4: FindPivots and Witnesses

## The role of pivots

A **pivot** is a source node that the recursive call will operate on.
Pivots are chosen from the input set `S` such that they have a "large enough
sub-tree" of nodes that can benefit from being processed together.

The intuition is this: not every node in `S` is worth recursing into. Some
sources are dead ends (no useful descendants), and processing them
individually wastes work. The pivot selection step picks the sources that
will *actually* drive the recursive expansion.

## What's a witness?

A **witness** is a node that has been touched during pivot selection but
isn't itself a pivot. Witnesses are bookkept so that:

1. The algorithm doesn't re-explore them in the next recursion level.
2. Their distances can be returned to the caller as part of the result.

In code, the `FindPivots` function returns two sets: `P` (pivots) and `W`
(witnesses, including the pivots themselves).

## The FindPivots procedure

Here's the algorithm in pseudocode (from Lemma 3.2 of the paper):

```
function FindPivots(graph, B, S, k):
    W   := S      # witnesses (initially the input)
    Wprev := S    # most recent expansion frontier

    repeat k times:
        Wi := empty set
        for u in Wprev:
            if dist[u] >= B: continue       # outside the bound
            for each edge (u, v, w):
                if dist[u] + w <= dist[v]:
                    dist[v] = dist[u] + w   # relax the edge
                    if dist[v] < B:
                        Wi.add(v)
        W := W ∪ Wi
        if |W| > k * |S|:
            # too many witnesses — fall back to all of S
            return P=S, W
        Wprev := Wi

    # Build a forest of "tight" edges within W
    # (edges where dist[v] == dist[u] + w exactly)
    children := defaultdict(list)
    indeg    := defaultdict(int)
    for u in W:
        for each edge (u, v, w):
            if v in W and dist[v] == dist[u] + w:
                children[u].append(v)
                indeg[v] += 1

    # Pick pivots: roots (indeg=0) of subtrees of size >= k
    P := empty set
    for u in S:
        if indeg[u] == 0 and subtree_size(u, children) >= k:
            P.add(u)
    return P, W
```

## What's happening here

1. **Bounded BFS expansion** (the first loop). Starting from `S`, expand
   outward `k` steps, relaxing edges as we go. Anything within distance
   `B` becomes a witness.

2. **Early termination.** If the witness set grows too large
   (`|W| > k * |S|`), we give up on the structure-finding step and
   fall back to using `S` itself as pivots.

3. **Build a tight-edge forest.** Within the witnesses, find edges that
   are *on a shortest path* from a source. These edges form a forest
   rooted at the sources.

4. **Select pivots.** A pivot is a source whose sub-tree (in the forest)
   has at least `k` nodes. Sources with small sub-trees are not pivots —
   they don't have enough "downstream" benefit to justify a recursive call.

## Why `k`?

`k` is the parameter `k = ⌊log^{1/3} n⌋` from the algorithm. It controls:

- How many BFS expansion steps we do (`k` iterations of the outer loop).
- The minimum sub-tree size for a node to qualify as a pivot.

The choice `log^{1/3} n` balances the work in each recursion level against
the total number of recursion levels. See
[PARAMETER_SENSITIVITY.md](../PARAMETER_SENSITIVITY.md) for details.

## A concrete example

Take our reference graph with `S = {s}`, `B = 10`, `k = 1`:

```
s -1-> a -2-> b -1-> c
       \5---/
```

After 1 step of bounded expansion:
- `a` is added to `Wi` (and `W`)
- `b` is added (via `s -> a -> b` would be 3, but only `s -> a` is the
  one-step expansion from `s`; `b` is added in the *next* iteration)

Actually wait — in the first iteration we expand from `Wprev = {s}` and
relax `s -> a`, so `Wi = {a}`. After the loop, `Wprev = {a}`.

Since `k=1`, that's the only iteration. `W = {s, a}`.

We then build the forest: `children[s] = [a]`, `indeg[a] = 1`.
Subtree of `s` has size 2 (≥ k=1), so `s` is a pivot.

Result: `P = {s}`, `W = {s, a}`.

## What can go wrong

`FindPivots` is **simplified** in many implementations because the full
forest construction is expensive on small graphs. The reference
implementations in this repository each take a slightly different approach:

- **C** and **Python** implement the full Lemma 3.2 with subtree sizes.
- **Rust** uses a simplified version that picks the first `k` nodes from `S`.
- **Go** matches the C version.

For the asymptotic analysis to hold, the full version is needed. The
simplified versions still produce correct shortest paths but may not hit
the optimal complexity bound on adversarial graphs.

## What's next?

Now that we have the building blocks (DQueue + FindPivots), [Tutorial 5](05-bmssp-recursion.md)
will assemble the recursive BMSSP algorithm itself.
