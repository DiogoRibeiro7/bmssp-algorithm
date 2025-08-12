from __future__ import annotations
from typing import Dict, List, Set, Tuple, Any
import math
import heapq
from collections import defaultdict
from dataclasses import dataclass

Node = Any
Weight = float


class Graph:
    """
    Graph represents a directed graph with non-negative edge weights.

    Attributes:
        adj (Dict[Node, List[Tuple[Node, Weight]]]):
            Adjacency list mapping each node to a list of (neighbor, weight) pairs.

    Methods:
        add_edge(u: Node, v: Node, w: Weight) -> None:
            Adds a directed edge from node u to node v with weight w.
            Raises ValueError if w is negative.

        neighbors(u: Node) -> List[Tuple[Node, Weight]]:
            Returns a list of (neighbor, weight) pairs for the given node u.
    """

    def __init__(self) -> None:
        self.adj: Dict[Node, List[Tuple[Node, Weight]]] = {}

    def add_edge(self, u: Node, v: Node, w: Weight) -> None:
        if w < 0:
            raise ValueError("Only non-negative weights allowed")
        self.adj.setdefault(u, []).append((v, float(w)))
        self.adj.setdefault(v, self.adj.get(v, []))

    def neighbors(self, u: Node) -> List[Tuple[Node, Weight]]:
        return self.adj.get(u, [])


# ------------------- DQueue from Lemma 3.3 -------------------
class DQueue:
    """
    DQueue is a specialized queue structure for managing nodes with associated
    distances, supporting batch operations and bounded by a distance threshold.

    Attributes:
        M (int): The maximum number of nodes to pull in a single batch.
        B (float): The distance threshold; nodes with distances >= B are
            ignored.
        data (List[Tuple[float, Node]]): Min-heap storing (distance, node) 
        pairs.
        prepend (List[Tuple[float, Node]]): List for batch-prepending nodes.

    Methods:
        insert(node: Node, dist: float) -> None:
            Insert a node with its distance into the queue if the distance is 
            less than B.

        batch_prepend(items: List[Tuple[Node, float]]) -> None:
            Batch prepend nodes with their distances if the distance is less 
            than B.

        pull() -> Tuple[float, Set[Node]]:
            Retrieve up to M nodes from the queue or prepend list, grouped by
            their distance.
            Returns a tuple of the smallest distance in the group and the set
            of nodes.

        non_empty() -> bool:
            Check if the queue contains any nodes.
    """

    def __init__(self, M: int, B: float):
        self.M = M
        self.B = B
        self.data: List[Tuple[float, Node]] = []
        self.prepend: List[Tuple[float, Node]] = []

    def insert(self, node: Node, dist: float) -> None:
        if dist >= self.B:
            return
        heapq.heappush(self.data, (dist, node))

    def batch_prepend(self, items: List[Tuple[Node, float]]) -> None:
        self.prepend.extend((dist, node) for node, dist in items if dist < self.B)

    def pull(self) -> Tuple[float, Set[Node]]:
        if self.prepend:
            group = self.prepend[: self.M]
            self.prepend = self.prepend[self.M :]
            B_i = group[0][0] if group else self.B
            return B_i, {node for _, node in group}

        if not self.data:
            return self.B, set()

        out: List[Tuple[float, Node]] = []
        while self.data and len(out) < self.M:
            dist, node = heapq.heappop(self.data)
            out.append((dist, node))
        B_i = out[0][0] if out else self.B
        return B_i, {node for _, node in out}

    def non_empty(self) -> bool:
        return bool(self.data or self.prepend)


# ------------------- Result containers for API consistency -------------------


@dataclass
class PivotResult:
    """Result of :func:`find_pivots` with the pivot set ``P`` and explored nodes ``W``."""

    P: Set[Node]
    W: Set[Node]


@dataclass
class BaseCaseResult:
    """Outcome of :func:`base_case` containing updated bound ``B`` and visited nodes ``U``."""

    B: float
    U: Set[Node]

@dataclass
class BMSSPResult:
    """Return value for :func:`bmssp` capturing the recursion bound ``B`` and finalized nodes ``U``."""

    B: float
    U: Set[Node]


# ------------------- Algorithm 1: FindPivots -------------------
def find_pivots(
    graph: Graph,
    B: float,
    S: Set[Node],
    d_hat: Dict[Node, float],
    complete: Set[Node],
    k: int,
    verbose: bool = False,
) -> PivotResult:
    """
    Finds pivot nodes in a graph based on distance constraints and subtree sizes.

    This function explores the graph starting from a set of source nodes `S`, updating tentative distances (`d_hat`) to other nodes, and expanding the search up to `k` steps or until a size threshold is exceeded. It then constructs a forest of reachable nodes and identifies pivot nodes as those in `S` whose subtrees (in the constructed forest) have size at least `k` and have no incoming edges within the forest.

    Args:
        graph (Graph): The graph object supporting neighbor iteration.
        B (float): Distance threshold; nodes with tentative distance >= B are not expanded.
        S (Set[Node]): Set of source nodes to start the search from.
        d_hat (Dict[Node, float]): Dictionary mapping nodes to their tentative distances.
        complete (Set[Node]): Set of nodes considered as already processed (not used in this function).
        k (int): Maximum number of expansion steps and minimum subtree size for pivots.

    Returns:
        PivotResult:
            - P: Set of pivot nodes in `S` whose subtrees have size at least `k` and no incoming edges in the forest.
            - W: Set of all nodes reached during the expansion.
    """
    W: Set[Node] = set(S)
    W_prev: Set[Node] = set(S)
    if verbose:
        print(f"find_pivots: start |S|={len(S)}, B={B}")

    for _ in range(1, k + 1):
        W_i: Set[Node] = set()
        for u in W_prev:
            du = d_hat[u]
            if du >= B:
                continue
            for v, w_uv in graph.neighbors(u):
                if du + w_uv <= d_hat[v]:
                    d_hat[v] = du + w_uv
                    if du + w_uv < B:
                        W_i.add(v)
        W |= W_i
        if len(W) > k * len(S):
            if verbose:
                print(
                    "find_pivots: early termination |W| > k*|S|",
                )
            return PivotResult(set(S), W)
        W_prev = W_i

    F_children: Dict[Node, List[Node]] = defaultdict(list)
    indeg: Dict[Node, int] = {u: 0 for u in W}
    for u in W:
        du = d_hat[u]
        for v, w_uv in graph.neighbors(u):
            if v in W and math.isclose(d_hat[v], du + w_uv, abs_tol=1e-12):
                F_children[u].append(v)
                indeg[v] += 1

    def subtree_size(u: Node) -> int:
        size = 1
        for child in F_children.get(u, []):
            size += subtree_size(child)
        return size

    P = {u for u in S if indeg.get(u, 0) == 0 and subtree_size(u) >= k}
    if verbose:
        print(f"find_pivots: pivots={P}")
    return PivotResult(P, W)


# ------------------- Algorithm 2: BaseCase -------------------
def base_case(
    graph: Graph,
    B: float,
    S: Set[Node],
    d_hat: Dict[Node, float],
    complete: Set[Node],
    k: int,
    verbose: bool = False,
) -> BaseCaseResult:
    """
    Finds a base case subset of nodes in the graph with respect to distance constraints.

    This function starts from an initial set of nodes `S` and expands a subset `U0` by exploring neighbors
    using a priority queue (min-heap) based on tentative distances `d_hat`. The expansion continues until
    `U0` contains at least `k + 1` nodes or the heap is exhausted. The function updates the `complete` set
    with visited nodes and maintains the shortest distances in `d_hat`. If the subset size is less than or
    equal to `k`, it returns the original bound `B` and the subset. Otherwise, it computes a new bound
    `B_prime` and returns the subset of nodes with distances strictly less than `B_prime`.

    Args:
        graph (Graph): The graph object supporting neighbor iteration.
        B (float): The current upper bound for distances.
        S (Set[Node]): The initial set of nodes to start the search from.
        d_hat (Dict[Node, float]): Dictionary mapping nodes to their tentative distances.
        complete (Set[Node]): Set to be updated with nodes that have been fully processed.
        k (int): The minimum number of nodes to include in the subset (returns when subset size exceeds k).

    Returns:
        BaseCaseResult: Updated bound and the subset of nodes found.
    """
    x = next(iter(S))
    U0: Set[Node] = {x}
    H: List[Tuple[float, Node]] = [(d_hat[x], x)]
    visited: Set[Node] = set()
    if verbose:
        print(f"base_case: start from {x} with B={B}")

    while H and len(U0) < k + 1:
        du, u = heapq.heappop(H)
        if u in visited:
            continue
        visited.add(u)
        U0.add(u)
        complete.add(u)
        for v, w_uv in graph.neighbors(u):
            if du + w_uv <= d_hat[v] and du + w_uv < B:
                d_hat[v] = du + w_uv
                heapq.heappush(H, (d_hat[v], v))

    if len(U0) <= k:
        if verbose:
            print("base_case: early termination |U0| <= k")
        return BaseCaseResult(B, U0)
    else:
        B_prime = max(d_hat[v] for v in U0)
        if verbose:
            print(f"base_case: computed B'={B_prime}")
        return BaseCaseResult(B_prime, {v for v in U0 if d_hat[v] < B_prime})


# ------------------- Algorithm 3: BMSSP -------------------
def bmssp(
    graph: Graph,
    l: int,
    B: float,
    S: Set[Node],
    d_hat: Dict[Node, float],
    complete: Set[Node],
    k: int,
    t: int,
    verbose: bool = False,
) -> BMSSPResult:
    """
    Performs a recursive bounded multi-source shortest paths (BMSSP) computation on a given graph.

    Args:
        graph (Graph): The input graph object supporting neighbor queries.
        l (int): The current recursion depth.
        B (float): The current distance bound.
        S (Set[Node]): The current set of source nodes.
        d_hat (Dict[Node, float]): Dictionary mapping nodes to their tentative shortest distances.
        complete (Set[Node]): Set of nodes for which shortest paths have been finalized.
        k (int): The maximum number of sources to consider at each recursion level.
        t (int): The branching factor exponent for recursion.

    Returns:
        BMSSPResult: Updated bound and set of nodes whose shortest paths were finalized in this recursion.
    """
    if verbose:
        print(f"bmssp: level={l}, B={B}, |S|={len(S)}")
    if l == 0:
        bc = base_case(graph, B, S, d_hat, complete, k, verbose)
        if verbose:
            print(f"bmssp: base case returns B={bc.B}, |U|={len(bc.U)}")
        return BMSSPResult(bc.B, bc.U)

    piv = find_pivots(graph, B, S, d_hat, complete, k, verbose)
    P, W = piv.P, piv.W
    if verbose:
        print(f"bmssp: pivots={P}")
    M = 2 ** ((l - 1) * t)
    D = DQueue(M, B)
    for x in P:
        D.insert(x, d_hat[x])

    U: Set[Node] = set()
    B0_prime = min(d_hat[x] for x in P) if P else B
    if verbose:
        print(f"bmssp: B0'={B0_prime}")

    while len(U) < k * (2 ** (l * t)) and D.non_empty():
        Bi, Si = D.pull()
        rec = bmssp(graph, l - 1, Bi, Si, d_hat, complete, k, t, verbose)
        B_prime_i, U_i = rec.B, rec.U
        U |= U_i
        K: List[Tuple[Node, float]] = []
        for u in U_i:
            for v, w_uv in graph.neighbors(u):
                if d_hat[u] + w_uv <= d_hat[v]:
                    d_hat[v] = d_hat[u] + w_uv
                    if Bi <= d_hat[v] < B:
                        D.insert(v, d_hat[v])
                    elif B_prime_i <= d_hat[v] < Bi:
                        K.append((v, d_hat[v]))
        prepend_items = K + [(x, d_hat[x]) for x in Si if B_prime_i <= d_hat[x] < Bi]
        D.batch_prepend(prepend_items)
    if verbose:
        if len(U) >= k * (2 ** (l * t)):
            reason = "U size reached"
        elif not D.non_empty():
            reason = "queue empty"
        else:
            reason = "condition false"
        print(f"bmssp: terminating loop due to {reason}")

    B_prime = min(B0_prime, B)
    U |= {x for x in W if d_hat[x] < B_prime}
    complete |= U
    if verbose:
        print(f"bmssp: returning B={B_prime}, |U|={len(U)}")
    return BMSSPResult(B_prime, U)


# ------------------- Main Driver -------------------
def run_sssp(graph: Graph, source: Node, verbose: bool = False) -> Dict[Node, float]:
    n = len(graph.adj)
    k = max(1, int(math.log(n, 2) ** (1 / 3)))  # ⌊log^{1/3} n⌋
    t = max(1, int(math.log(n, 2) ** (2 / 3)))  # ⌊log^{2/3} n⌋
    l = math.ceil(math.log(n, 2) / t)  # ⌈log n / t⌉

    d_hat = {v: math.inf for v in graph.adj}
    d_hat[source] = 0.0
    complete: Set[Node] = {source}

    bmssp(graph, l, math.inf, {source}, d_hat, complete, k, t, verbose)
    return d_hat


# ------------------- Example -------------------
if __name__ == "__main__":
    g = Graph()
    g.add_edge("s", "a", 1)
    g.add_edge("s", "b", 4)
    g.add_edge("a", "b", 2)
    g.add_edge("a", "c", 5)
    g.add_edge("b", "c", 1)

    dist = run_sssp(g, "s")
    print("Distances from s:", dist)
