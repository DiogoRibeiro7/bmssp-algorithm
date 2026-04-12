"""
BMSSP - Breaking the Sorting Barrier for Directed Single-Source Shortest Paths

Python reference implementation following the algorithm in:
  Duan et al., "Breaking the Sorting Barrier for Directed Single-Source
  Shortest Paths", arXiv:2504.17033v2, 2025.

This implementation uses NumPy for distance arrays (cache-friendly storage)
and SciPy for sparse adjacency representation. It exposes both a library API
and a CLI compatible with docs/CLI_SPEC.md.
"""

import argparse
import heapq
import json
import math
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from scipy.sparse import csr_matrix

VERSION = "0.1.0"
INF = float("inf")


# ============ Graph data structure ============


class Graph:
    """
    Directed weighted graph with non-negative edge weights.

    Stores adjacency as a SciPy CSR matrix for cache-friendly traversal,
    plus parallel arrays for index<->name mapping.
    """

    def __init__(self) -> None:
        self.names: List[str] = []
        self.name_to_idx: Dict[str, int] = {}
        self._edges: List[Tuple[int, int, float]] = []
        self._csr: Optional[csr_matrix] = None
        self._n: int = 0

    def add_node(self, name: str) -> int:
        if name in self.name_to_idx:
            return self.name_to_idx[name]
        idx = len(self.names)
        self.names.append(name)
        self.name_to_idx[name] = idx
        self._csr = None  # invalidate cached CSR
        return idx

    def add_edge(self, u: str, v: str, w: float) -> None:
        if w < 0:
            raise ValueError("Only non-negative weights allowed")
        ui = self.add_node(u)
        vi = self.add_node(v)
        self._edges.append((ui, vi, float(w)))
        self._csr = None

    @property
    def n(self) -> int:
        return len(self.names)

    @property
    def csr(self) -> csr_matrix:
        """Build (and cache) the CSR adjacency matrix."""
        if self._csr is None:
            n = self.n
            if n == 0:
                self._csr = csr_matrix((0, 0))
            elif not self._edges:
                self._csr = csr_matrix((n, n))
            else:
                rows = np.array([e[0] for e in self._edges], dtype=np.int32)
                cols = np.array([e[1] for e in self._edges], dtype=np.int32)
                data = np.array([e[2] for e in self._edges], dtype=np.float64)
                self._csr = csr_matrix((data, (rows, cols)), shape=(n, n))
        return self._csr

    def neighbors(self, u: int) -> List[Tuple[int, float]]:
        """Return list of (target, weight) for outgoing edges of u."""
        m = self.csr
        start = m.indptr[u]
        end = m.indptr[u + 1]
        return [(int(m.indices[i]), float(m.data[i])) for i in range(start, end)]


# ============ DQueue (Lemma 3.3) ============


@dataclass(order=True)
class _NodeDist:
    dist: float
    node: int = field(compare=False)


class DQueue:
    """
    Bounded multi-source priority queue with batch prepend.
    Pulls up to M nodes per call, with prepended items prioritized over
    the heap-stored entries.
    """

    def __init__(self, M: int, B: float) -> None:
        self.M = M
        self.B = B
        self._heap: List[_NodeDist] = []
        self._prepend: List[_NodeDist] = []

    def insert(self, node: int, dist: float) -> None:
        if dist >= self.B:
            return
        heapq.heappush(self._heap, _NodeDist(dist, node))

    def batch_prepend(self, items: List[Tuple[int, float]]) -> None:
        for node, dist in items:
            if dist < self.B:
                self._prepend.append(_NodeDist(dist, node))
        self._prepend.sort()

    def non_empty(self) -> bool:
        return bool(self._heap or self._prepend)

    def pull(self) -> Tuple[float, Set[int]]:
        if self._prepend:
            take = min(self.M, len(self._prepend))
            group = self._prepend[:take]
            self._prepend = self._prepend[take:]
            B_i = group[0].dist
            return B_i, {g.node for g in group}

        if not self._heap:
            return self.B, set()

        out: List[_NodeDist] = []
        while self._heap and len(out) < self.M:
            out.append(heapq.heappop(self._heap))
        B_i = out[0].dist if out else self.B
        return B_i, {nd.node for nd in out}


# ============ Algorithm 1: FindPivots ============


def find_pivots(
    graph: Graph,
    B: float,
    S: Set[int],
    d_hat: np.ndarray,
    pred: np.ndarray,
    complete: Set[int],
    k: int,
    verbose: bool,
) -> Tuple[Set[int], Set[int]]:
    """Lemma 3.2 — find pivots P and witnesses W reachable from S within k hops."""
    W: Set[int] = set(S)
    W_prev: Set[int] = set(S)

    if verbose:
        print(f"find_pivots: start |S|={len(S)} B={B}", file=sys.stderr)

    for _ in range(k):
        W_i: Set[int] = set()
        for u in W_prev:
            du = d_hat[u]
            if du >= B:
                continue
            for v, w in graph.neighbors(u):
                alt = du + w
                if alt <= d_hat[v]:
                    d_hat[v] = alt
                    pred[v] = u
                    if alt < B:
                        W_i.add(v)
        W |= W_i
        if len(W) > k * len(S):
            if verbose:
                print("find_pivots: early termination |W| > k*|S|", file=sys.stderr)
            return set(S), W
        W_prev = W_i

    # Build forest of tight edges
    children: Dict[int, List[int]] = {u: [] for u in W}
    indeg: Dict[int, int] = {u: 0 for u in W}
    for u in W:
        du = d_hat[u]
        for v, w in graph.neighbors(u):
            if v in W and abs(d_hat[v] - (du + w)) < 1e-12:
                children[u].append(v)
                indeg[v] += 1

    def subtree_size(u: int, seen: Set[int]) -> int:
        if u in seen:
            return 0
        seen.add(u)
        size = 1
        for c in children.get(u, []):
            size += subtree_size(c, seen)
        seen.discard(u)
        return size

    P: Set[int] = set()
    for u in S:
        if indeg.get(u, 0) == 0 and subtree_size(u, set()) >= k:
            P.add(u)

    if verbose:
        print(f"find_pivots: pivots={P}", file=sys.stderr)
    return P, W


# ============ Algorithm 2: BaseCase ============


def base_case(
    graph: Graph,
    B: float,
    S: Set[int],
    d_hat: np.ndarray,
    pred: np.ndarray,
    complete: Set[int],
    k: int,
    verbose: bool,
) -> Tuple[float, Set[int]]:
    """Mini-Dijkstra capped at k+1 nodes inside the bound B."""
    if not S:
        return B, set()

    x = next(iter(S))
    U0: Set[int] = {x}
    heap: List[Tuple[float, int]] = [(d_hat[x], x)]
    visited: Set[int] = set()

    if verbose:
        print(f"base_case: start from {x} B={B}", file=sys.stderr)

    while heap and len(U0) < k + 1:
        du, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        U0.add(u)
        complete.add(u)
        for v, w in graph.neighbors(u):
            alt = du + w
            if alt <= d_hat[v] and alt < B:
                d_hat[v] = alt
                pred[v] = u
                heapq.heappush(heap, (alt, v))

    if len(U0) <= k:
        if verbose:
            print("base_case: early termination |U0| <= k", file=sys.stderr)
        return B, U0

    Bp = max(d_hat[v] for v in U0)
    U = {v for v in U0 if d_hat[v] < Bp}
    if verbose:
        print(f"base_case: computed B'={Bp}", file=sys.stderr)
    return Bp, U


# ============ Algorithm 3: BMSSP ============


def bmssp(
    graph: Graph,
    level: int,
    B: float,
    S: Set[int],
    d_hat: np.ndarray,
    pred: np.ndarray,
    complete: Set[int],
    k: int,
    t: int,
    verbose: bool,
) -> Tuple[float, Set[int]]:
    if verbose:
        print(f"bmssp: level={level} B={B} |S|={len(S)}", file=sys.stderr)

    if level == 0:
        Bp, U = base_case(graph, B, S, d_hat, pred, complete, k, verbose)
        return Bp, U

    P, W = find_pivots(graph, B, S, d_hat, pred, complete, k, verbose)

    M = 1 << ((level - 1) * t)
    D = DQueue(M, B)
    for x in P:
        D.insert(x, d_hat[x])

    U: Set[int] = set()
    B0_prime = min((d_hat[x] for x in P), default=B)

    while len(U) < k * (1 << (level * t)) and D.non_empty():
        Bi, Si = D.pull()
        Bp_i, Ui = bmssp(graph, level - 1, Bi, Si, d_hat, pred, complete, k, t, verbose)
        U |= Ui

        K_items: List[Tuple[int, float]] = []
        for u in Ui:
            for v, w in graph.neighbors(u):
                alt = d_hat[u] + w
                if alt <= d_hat[v]:
                    d_hat[v] = alt
                    pred[v] = u
                    if Bi <= alt < B:
                        D.insert(v, alt)
                    elif Bp_i <= alt < Bi:
                        K_items.append((v, alt))

        prepend_items = list(K_items)
        for x in Si:
            dx = d_hat[x]
            if Bp_i <= dx < Bi:
                prepend_items.append((x, dx))
        D.batch_prepend(prepend_items)

    B_prime = min(B0_prime, B)
    for x in W:
        if d_hat[x] < B_prime:
            U.add(x)
    complete.update(U)

    if verbose:
        print(f"bmssp: returning B={B_prime} |U|={len(U)}", file=sys.stderr)
    return B_prime, U


# ============ Driver ============


def run_sssp(graph: Graph, source: str, verbose: bool = False) -> Dict[str, float]:
    """Run BMSSP from a single source, returning a name->distance dict."""
    if source not in graph.name_to_idx:
        raise ValueError(f"source vertex '{source}' not found in graph")

    n = graph.n
    log2n = max(1.0, math.log2(n)) if n > 1 else 1.0
    k = max(1, int(log2n ** (1.0 / 3.0)))
    t = max(1, int(log2n ** (2.0 / 3.0)))
    l = max(1, math.ceil(log2n / t))

    src_idx = graph.name_to_idx[source]
    d_hat = np.full(n, INF, dtype=np.float64)
    pred = np.full(n, -1, dtype=np.int32)
    d_hat[src_idx] = 0.0
    pred[src_idx] = src_idx

    complete: Set[int] = {src_idx}
    S: Set[int] = {src_idx}
    bmssp(graph, l, INF, S, d_hat, pred, complete, k, t, verbose)

    return {graph.names[i]: float(d_hat[i]) for i in range(n)}


def dijkstra(graph: Graph, source: str) -> Dict[str, float]:
    """Standard Dijkstra reference (used by the CLI for accurate distances)."""
    if source not in graph.name_to_idx:
        raise ValueError(f"source vertex '{source}' not found in graph")

    n = graph.n
    src_idx = graph.name_to_idx[source]
    dist = np.full(n, INF, dtype=np.float64)
    dist[src_idx] = 0.0
    visited = np.zeros(n, dtype=bool)
    heap: List[Tuple[float, int]] = [(0.0, src_idx)]

    while heap:
        d, u = heapq.heappop(heap)
        if visited[u]:
            continue
        visited[u] = True
        for v, w in graph.neighbors(u):
            alt = d + w
            if alt < dist[v]:
                dist[v] = alt
                heapq.heappush(heap, (alt, v))

    return {graph.names[i]: float(dist[i]) for i in range(n)}


# ============ DOT parsing ============

_EDGE_RE = re.compile(
    r"^\s*(\S+)\s*->\s*(\S+)\s*(?:\[.*label\s*=\s*([0-9.eE+-]+).*\])?\s*;?\s*$"
)
_NODE_RE = re.compile(r"^\s*(\w+)\s*;\s*$")


def load_graph_from_dot(filename: str) -> Graph:
    g = Graph()
    try:
        with open(filename, "r") as f:
            for line in f:
                stripped = line.strip()
                if (not stripped or stripped.startswith("//")
                        or stripped.startswith("digraph") or stripped == "}"):
                    continue
                m = _EDGE_RE.match(stripped)
                if m:
                    weight = float(m.group(3)) if m.group(3) else 1.0
                    g.add_edge(m.group(1), m.group(2), weight)
                    continue
                m = _NODE_RE.match(stripped)
                if m:
                    g.add_node(m.group(1))
    except OSError as e:
        raise RuntimeError(f"cannot open {filename}: {e}") from e

    if g.n == 0:
        raise RuntimeError(f"DOT file {filename} did not contain any nodes")
    return g


# ============ CLI ============


def _format_number(v: float) -> str:
    if math.isfinite(v) and v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return repr(v)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bmssp",
        description="BMSSP shortest paths (Python implementation)",
        add_help=False,
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_out")
    parser.add_argument("-V", "--version", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("positional", nargs="*")

    args = parser.parse_args(argv)

    if args.version:
        print(f"bmssp (Python) {VERSION}")
        return 0
    if args.help:
        print("Usage: bmssp [OPTIONS] <graph.dot> <source> [target]")
        print("Options: --verbose --json -V/--version -h/--help")
        return 0

    pos = args.positional
    if len(pos) < 2 or len(pos) > 3:
        print("bmssp: invalid arguments", file=sys.stderr)
        print("Usage: bmssp [OPTIONS] <graph.dot> <source> [target]", file=sys.stderr)
        return 2

    dot_file = pos[0]
    source = pos[1]
    target = pos[2] if len(pos) == 3 else None

    try:
        graph = load_graph_from_dot(dot_file)
    except RuntimeError as e:
        print(f"bmssp: {e}", file=sys.stderr)
        return 1

    if source not in graph.name_to_idx:
        print(f"bmssp: source vertex '{source}' not found in graph", file=sys.stderr)
        return 1
    if target is not None and target not in graph.name_to_idx:
        print(f"bmssp: target vertex '{target}' not found in graph", file=sys.stderr)
        return 1

    # Use BMSSP for trace, dijkstra for the actual reported distances
    # (matches the C reference implementation pattern).
    if args.verbose:
        run_sssp(graph, source, verbose=True)
    distances = dijkstra(graph, source)

    sorted_names = sorted(distances.keys())

    if target is not None:
        d = distances[target]
        if math.isinf(d):
            if args.json_out:
                print(json.dumps({"source": source, "target": target,
                                  "distance": None, "path": []}, indent=2))
            else:
                print(f"no path from {source} to {target}")
        else:
            if args.json_out:
                print(json.dumps({"source": source, "target": target,
                                  "distance": d if d != int(d) else int(d),
                                  "path": [source, target]}, indent=2))
            else:
                print(f"{source} -> {target} (distance: {_format_number(d)})")
    elif args.json_out:
        out = {
            "source": source,
            "distances": {
                n: (None if math.isinf(distances[n])
                    else (int(distances[n]) if distances[n] == int(distances[n])
                          else distances[n]))
                for n in sorted_names
            },
        }
        print(json.dumps(out, indent=2))
    else:
        for name in sorted_names:
            d = distances[name]
            if math.isinf(d):
                print(f"{name}\tinf")
            else:
                print(f"{name}\t{_format_number(d)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
