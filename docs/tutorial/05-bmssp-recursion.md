# Tutorial 5: Putting It Together — The BMSSP Recursion

## The full algorithm

We now have all the pieces:
- **DQueue** (Lemma 3.3) — bounded priority queue with batch operations
- **FindPivots** (Lemma 3.2) — pivot selection
- **BaseCase** — bounded Dijkstra for small instances

Algorithm 3 in the paper combines them into the recursive **BMSSP** procedure.
Here's the structure:

```
function BMSSP(graph, l, B, S):
    if l == 0:
        return BaseCase(graph, B, S)

    P, W := FindPivots(graph, B, S, k)

    M := 2^((l-1) * t)            # batch size for this level
    D := new DQueue(M, B)
    for x in P:
        D.insert(x, dist[x])

    U := empty set                 # finalized nodes
    B0_prime := min(dist[x] for x in P)

    while |U| < k * 2^(l*t) and D.non_empty():
        Bi, Si := D.pull()         # next batch
        Bi_prime, Ui := BMSSP(graph, l-1, Bi, Si)   # recurse one level down

        U := U ∪ Ui

        # Edge relaxation from finalized nodes
        K := []
        for u in Ui:
            for each edge (u, v, w):
                alt := dist[u] + w
                if alt <= dist[v]:
                    dist[v] = alt
                    if Bi <= alt < B:
                        D.insert(v, alt)
                    elif Bi_prime <= alt < Bi:
                        K.append((v, alt))

        # Prepend the "near" items so the next pull returns them
        prepend := K
        for x in Si:
            if Bi_prime <= dist[x] < Bi:
                prepend.append((x, dist[x]))
        D.batch_prepend(prepend)

    B_prime := min(B0_prime, B)
    for x in W:
        if dist[x] < B_prime:
            U.add(x)

    return B_prime, U
```

## What's going on?

Read it from the inside out:

1. **At the deepest level (l=0)**, we just run a bounded Dijkstra
   (`BaseCase`), capped at `k+1` nodes.
2. **At each level above**, we use FindPivots to pick promising sources,
   set up a DQueue, and pull batches.
3. **Each pulled batch** becomes the input to a recursive call one level
   down. The recursive call returns a smaller bound `Bi_prime` and a set
   of finalized nodes `Ui`.
4. **After the recursive call**, we relax edges out of `Ui` and reinsert
   the resulting tentative distances into the DQueue. The "prepend" trick
   keeps near-bound items in front for the next pull.
5. **The loop terminates** when either the DQueue is empty or we've finalized
   enough nodes (`|U| >= k * 2^(l*t)`).

## Why these constants?

The parameters are tuned to balance:

- `k = ⌊log^{1/3} n⌋` — pivot count and base case size
- `t = ⌊log^{2/3} n⌋` — exponent for the recursion
- `l = ⌈log n / t⌉` — number of recursion levels

So `2^(l*t) ≈ n`, meaning the top level finalizes roughly all `n` nodes.
At each level, the DQueue's batch size `M = 2^((l-1)*t)` is large enough
to hold a fraction of the next-lower level's finalized set.

The algebra works out so that the total work across all levels is:

$$O\left(\sum_{i=0}^{l} m \cdot \frac{2^{(i+1)t}}{2^{it}}\right) = O(m \cdot l \cdot 2^t) = O(m \cdot \log^{2/3} n)$$

(See the paper for the formal analysis.)

## Edge cases

- **`B = ∞`** (top-level call): All edges are eligible. The recursion
  finalizes everything reachable from the source.
- **`|S| = 1`** (start of recursion): Only the original source. After
  FindPivots, we may have 0 or 1 pivots.
- **Disconnected nodes**: Stay at distance `∞`, never finalized.

## How does this compare to Dijkstra?

Visually:

```
                           Dijkstra:
                           extract → relax → extract → relax → ...
                           (one node per extraction)

                           BMSSP (level l):
                           pull batch → recurse → relax batch → pull batch → ...
                           (M nodes per pull)

                           BMSSP (level 0):
                           bounded Dijkstra capped at k+1 nodes
```

The savings come from doing fewer total extractions while still
finalizing nodes in (approximately) the right order.

## Mental model

Think of BMSSP as a **multi-level skip list over Dijkstra**. Higher levels
process larger batches with looser bounds; lower levels do precise work
within each batch's narrow distance range. The recursion structure ensures
no node is processed at the wrong level.

## What's next?

[Tutorial 6](06-implementation.md) walks through the actual code in this
repository, showing how the abstract algorithm maps to concrete data
structures in C, Go, Rust, and Python.
