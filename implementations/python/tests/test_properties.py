import os
import sys
import math
import networkx as nx
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from bmssp import Graph, run_sssp
from hypothesis import given, strategies as st, settings

@st.composite
def small_graphs(draw):
    n = draw(st.integers(min_value=1, max_value=4))
    nodes = [chr(ord('a') + i) for i in range(n)]
    g = Graph()
    for node in nodes:
        g.adj.setdefault(node, [])
    for u in nodes:
        for v in nodes:
            if u == v:
                continue
            if draw(st.booleans()):
                w = draw(st.floats(min_value=0.1, max_value=10, allow_nan=False, allow_infinity=False))
                g.add_edge(u, v, w)
    source = nodes[0]
    return g, source

@given(small_graphs())
@settings(max_examples=25)
def test_distance_properties(data):
    g, src = data
    dist = run_sssp(g, src)
    assert dist[src] == 0
    for d in dist.values():
        assert d >= 0 or math.isinf(d)
    nxg = nx.DiGraph()
    for u, nbrs in g.adj.items():
        for v, w in nbrs:
            nxg.add_edge(u, v, weight=w)
    try:
        expected = nx.single_source_dijkstra_path_length(nxg, src, weight="weight")
    except Exception:
        expected = {}
    for node, exp in expected.items():
        if node in dist and not math.isinf(dist[node]):
            assert dist[node] >= exp - 1e-9
