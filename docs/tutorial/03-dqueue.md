# Tutorial 3: The DQueue Data Structure

## What is the DQueue?

The **DQueue** is the bounded priority queue used inside BMSSP. It's
described in Lemma 3.3 of the paper. Compared to a plain priority queue,
it adds three properties:

1. **An upper bound `B`.** Anything inserted with distance `≥ B` is silently
   dropped.
2. **A maximum batch size `M`.** Each `Pull()` returns up to `M` items, not
   just one.
3. **A batch-prepend operation.** Items can be added with priority *higher*
   than anything currently in the queue, jumping to the front.

The combination of these makes the DQueue cheap enough to support the
bounded multi-source primitive without paying log-n cost per operation.

## Operations

| Op | What it does |
|----|--------------|
| `Insert(node, dist)` | Add `(node, dist)` to the queue if `dist < B`. |
| `BatchPrepend(items)` | Add a batch of items at higher priority than any current item. |
| `Pull()` | Return up to `M` smallest items as a single batch. |
| `NonEmpty()` | True if the queue has any items. |

The key data layout is **two stacks**:

```
prepend list   ─┐
                ├──> Pull() takes from prepend first, then heap
heap            ─┘
```

Items inserted via `Insert` go into the heap (sorted by distance).
Items added via `BatchPrepend` go onto the `prepend` list, and `Pull()`
serves them first — they have higher priority than the heap by construction.

## A walkthrough

Say `M = 3` and `B = 100`. Start with an empty DQueue.

```
Insert(a, 10)
Insert(b, 5)
Insert(c, 20)
Insert(d, 7)

State:
  prepend: []
  heap: [b:5, d:7, a:10, c:20]   (min-heap)

Pull()  →  B_i = 5, nodes = {b, d, a}    (top 3 of heap)

State:
  prepend: []
  heap: [c:20]
```

Now we batch-prepend two items that should be processed *next*, before `c`:

```
BatchPrepend([(x, 8), (y, 12)])

State:
  prepend: [x:8, y:12]
  heap: [c:20]

Pull()  →  B_i = 8, nodes = {x, y}    (top 2 of prepend)

State:
  prepend: []
  heap: [c:20]
```

`c:20` is still waiting; the prepended items got served first.

## Why does this matter?

In standard Dijkstra, every relaxed edge causes a `decrease-key` (or a
fresh insert with stale entries). Each operation costs O(log n).

In BMSSP, the recursive structure produces *batches* of edges to relax. The
DQueue lets the algorithm:

1. **Insert** new tentative distances during recursion (heap operations,
   amortized cheap because of the batch size bound).
2. **Batch-prepend** the results of a recursive call back into the parent's
   queue, in O(1) amortized per item (the prepend list is just appended to).
3. **Pull a batch of M** in roughly O(M log M) time, then process the batch
   together rather than per-element.

The total work across all DQueue operations in BMSSP is `O(m * log^{2/3} n)`,
which is the headline complexity of the algorithm.

## Implementation in C

The C reference uses a struct with a binary min-heap and a prepend array:

```c
typedef struct {
    int M;
    double B;
    MinHeap data;            // standard binary heap
    NodeDist *prepend;        // prepend list
    int pre_count;
    int pre_capacity;
} DQueue;

void dq_insert(DQueue *dq, int node, double dist) {
    if (dist >= dq->B) return;
    heap_push(&dq->data, (NodeDist){dist, node});
}

void dq_batch_prepend(DQueue *dq, NodeDist *items, int count) {
    for (int i = 0; i < count; i++) {
        if (items[i].dist < dq->B) {
            // grow prepend if needed
            dq->prepend[dq->pre_count++] = items[i];
        }
    }
}
```

The full code is in [implementations/c/bmssp.c](../../implementations/c/bmssp.c)
around line 322.

## Why is this called a queue?

It's a misnomer — it's more accurately a **bounded priority queue with
batched front insertion**. The "queue" terminology in the paper reflects the
fact that consumers see a sequence of batches in roughly increasing distance
order.

## What's next?

In [Tutorial 4](04-find-pivots.md) we'll see how BMSSP picks **pivots** —
the special source nodes that drive the recursion. This is Lemma 3.2 in
the paper.
