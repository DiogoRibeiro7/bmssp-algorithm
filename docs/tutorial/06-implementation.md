# Tutorial 6: Implementing BMSSP

This tutorial walks through how the BMSSP recursion maps to actual code in
the reference implementations. We'll focus on C and Python; the other
languages follow the same structure.

## Files to read along with

- [implementations/c/bmssp.c](../../implementations/c/bmssp.c)
- [implementations/python/bmssp.py](../../implementations/python/bmssp.py)
- [implementations/rust/src/lib.rs](../../implementations/rust/src/lib.rs)
- [implementations/go/bmssp.go](../../implementations/go/bmssp.go)

## Step 1: Graph data structure

The graph is stored as an **adjacency list**. In C:

```c
typedef struct { int to; double w; } Edge;
typedef struct {
    Edge *edges;
    int count;
    int capacity;
} EdgeList;

typedef struct {
    int n;
    EdgeList *adj;
} Graph;
```

In Python (using SciPy CSR):

```python
class Graph:
    def __init__(self):
        self.names = []
        self.name_to_idx = {}
        self._edges = []
        self._csr = None  # built lazily
```

The CSR format gives us cache-friendly iteration over a single node's edges.

## Step 2: DQueue

Two storage areas: a heap and a prepend list.

C:
```c
typedef struct {
    int M;
    double B;
    MinHeap data;
    NodeDist *prepend;
    int pre_count;
    int pre_capacity;
} DQueue;
```

Python:
```python
class DQueue:
    def __init__(self, M, B):
        self.M = M
        self.B = B
        self._heap = []
        self._prepend = []
```

The `pull()` operation services the prepend list first, then falls back
to the heap. This is what gives recursive calls priority over the
parent's queue.

## Step 3: Distance and predecessor arrays

These are passed by reference through the recursion. In C:

```c
double *d_hat;   // tentative distances
int *pred;       // predecessor for path reconstruction
IntArray complete;  // finalized nodes
```

In Python (NumPy):

```python
d_hat = np.full(n, INF, dtype=np.float64)
pred = np.full(n, -1, dtype=np.int32)
complete = set()
```

The arrays are shared across all recursion levels — modifications at level
0 are visible to level `l`. This is essential for the algorithm: deeper
recursive calls discover better distances, and the parent loop sees them
on the next iteration.

## Step 4: BaseCase

When the recursion bottoms out, we run a small Dijkstra capped at `k+1`
nodes. C:

```c
BaseCaseResult base_case(Graph *graph, double B, IntArray *S,
                         double *d_hat, int *pred,
                         IntArray *complete, int k, int verbose) {
    int x = S->data[0];
    IntArray U0; ia_init(&U0); ia_add_unique(&U0, x);
    MinHeap H; heap_init(&H);
    heap_push(&H, (NodeDist){d_hat[x], x});

    while (!heap_empty(&H) && U0.count < k + 1) {
        NodeDist nd = heap_pop(&H);
        int u = nd.node;
        ...
        // relax edges
    }

    if (U0.count <= k) {
        return (BaseCaseResult){B, U0};
    }

    // Compute B' as the max distance in U0
    double Bp = -INFINITY;
    for (int i = 0; i < U0.count; i++) {
        if (d_hat[U0.data[i]] > Bp) Bp = d_hat[U0.data[i]];
    }
    return (BaseCaseResult){Bp, U_prime};
}
```

The early termination at `k+1` is what keeps the base case from doing
all the work itself.

## Step 5: FindPivots

The bounded BFS expansion + forest construction. Python:

```python
def find_pivots(graph, B, S, d_hat, pred, complete, k, verbose):
    W = set(S)
    W_prev = set(S)

    for _ in range(k):
        W_i = set()
        for u in W_prev:
            if d_hat[u] >= B: continue
            for v, w in graph.neighbors(u):
                alt = d_hat[u] + w
                if alt <= d_hat[v]:
                    d_hat[v] = alt
                    if alt < B: W_i.add(v)
        W |= W_i
        if len(W) > k * len(S):
            return set(S), W
        W_prev = W_i

    # Build forest, compute subtree sizes, select pivots
    children = {u: [] for u in W}
    indeg = {u: 0 for u in W}
    for u in W:
        for v, w in graph.neighbors(u):
            if v in W and abs(d_hat[v] - (d_hat[u] + w)) < 1e-12:
                children[u].append(v)
                indeg[v] += 1

    P = set()
    for u in S:
        if indeg.get(u, 0) == 0 and subtree_size(u, set()) >= k:
            P.add(u)
    return P, W
```

The `1e-12` tolerance for floating-point equality matters: edges on the
shortest path satisfy `dist[v] = dist[u] + w` exactly, but rounding can
introduce tiny errors.

## Step 6: BMSSP recursion

The main loop. C:

```c
BMSSPResult bmssp(Graph *graph, int l, double B, IntArray *S, ...) {
    if (l == 0) {
        BaseCaseResult bc = base_case(...);
        return (BMSSPResult){bc.B, bc.U};
    }

    PivotResult piv = find_pivots(...);
    int M = 1 << ((l - 1) * t);
    DQueue D; dq_init(&D, M, B);
    for (int i = 0; i < piv.P.count; i++) dq_insert(&D, piv.P.data[i], d_hat[piv.P.data[i]]);

    IntArray U; ia_init(&U);
    while (U.count < k * (1 << (l * t)) && dq_non_empty(&D)) {
        double Bi; IntArray Si;
        dq_pull(&D, &Bi, &Si);
        BMSSPResult rec = bmssp(graph, l - 1, Bi, &Si, ...);
        // Relax edges from rec.U, manage prepend list
        ...
    }
    ...
}
```

Note the **shared state**: `d_hat`, `pred`, `complete` are passed as
pointers (or by reference in higher-level languages). The recursion
mutates these in place.

## Step 7: Driver

The `run_sssp` driver picks parameters and starts the recursion:

```python
def run_sssp(graph, source, verbose=False):
    n = graph.n
    log2n = max(1.0, math.log2(n))
    k = max(1, int(log2n ** (1/3)))
    t = max(1, int(log2n ** (2/3)))
    l = max(1, math.ceil(log2n / t))

    src_idx = graph.name_to_idx[source]
    d_hat = np.full(n, INF)
    d_hat[src_idx] = 0.0
    pred = np.full(n, -1, dtype=np.int32)
    complete = {src_idx}
    S = {src_idx}

    bmssp(graph, l, INF, S, d_hat, pred, complete, k, t, verbose)
    return {graph.names[i]: float(d_hat[i]) for i in range(n)}
```

## A note on correctness vs. CLI behavior

You may notice that the CLI implementations call **Dijkstra**, not
`run_sssp`, for the actual reported distances. Why?

BMSSP is **bounded** — at small graph sizes, it may not explore all
reachable nodes (the recursion terminates early when `|U|` is large enough,
but on tiny graphs this leaves some nodes at distance `∞`). For correctness
on the CLI's example output, we run Dijkstra after-the-fact and report
those distances. The BMSSP recursion is exercised via `--verbose` for the
algorithm trace.

This is the same trade-off the C reference implementation makes.

## What's next?

[Tutorial 7](07-when-to-use.md) is the most practical: when should you
actually pick BMSSP over Dijkstra in real code?
