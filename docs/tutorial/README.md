# Understanding BMSSP — Step by Step

A tutorial series for understanding the **Breaking the Sorting Barrier**
algorithm by Duan et al. (2025), starting from familiar shortest-path concepts
and building up to the full recursive structure of BMSSP.

## Audience

These tutorials assume:
- Comfort with reading pseudocode
- Basic data structure knowledge (heaps, hash maps)
- Familiarity with Dijkstra's algorithm and asymptotic notation

No prior exposure to advanced shortest-path theory is required.

## Tutorials

| # | Title | Topic |
|---|-------|-------|
| 1 | [The Sorting Barrier](01-sorting-barrier.md) | Why classical SSSP is bound by O(m + n log n) |
| 2 | [Bounded Multi-Source Search](02-bounded-multi-source.md) | The key insight that enables the speedup |
| 3 | [The DQueue Data Structure](03-dqueue.md) | Lemma 3.3 and bounded batch operations |
| 4 | [FindPivots and Witnesses](04-find-pivots.md) | Lemma 3.2 — pivot selection |
| 5 | [Putting It Together](05-bmssp-recursion.md) | The full recursive BMSSP algorithm |
| 6 | [Implementing BMSSP](06-implementation.md) | Code walkthrough across languages |
| 7 | [When to Use BMSSP](07-when-to-use.md) | Practical guidance and pitfalls |

## Reading Order

The tutorials build on each other; read them in order. Each one is short
(~5–10 min) and includes worked examples on the reference graph used
throughout the repository.

## Reference Graph

We'll use this 4-node graph throughout the tutorial series:

```
   1     2
s ---> a ---> b
 \           ^
  \    5    /1
   \-> b ->c
       4
```

(`s -> a` weight 1, `s -> b` weight 4, `a -> b` weight 2, `a -> c` weight 5,
`b -> c` weight 1)

The shortest distances from `s`:
- `s -> s`: 0
- `s -> a`: 1 (via direct edge)
- `s -> b`: 3 (via `s -> a -> b`)
- `s -> c`: 4 (via `s -> a -> b -> c`)

## Related Resources

- [bmssp-walkthrough.md](../bmssp-walkthrough.md) — algorithm reference
- [PARAMETER_SENSITIVITY.md](../PARAMETER_SENSITIVITY.md) — k, t, l parameter analysis
- [PLATFORM_OPTIMIZATIONS.md](../PLATFORM_OPTIMIZATIONS.md) — implementation tuning
- [BMSSP_VS_DIJKSTRA.md](../BMSSP_VS_DIJKSTRA.md) — practical comparison

The original paper:
> Ran Duan, Jiayi Mao, Xinkai Shu, Longhui Yin.
> "Breaking the Sorting Barrier for Directed Single-Source Shortest Paths."
> arXiv:2504.17033v2, 2025.
