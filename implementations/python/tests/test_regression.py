import os
import sys
import math
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from bmssp import Graph, run_sssp


def test_regression_simple_path():
    g = Graph()
    g.add_edge("s", "a", 1)
    g.add_edge("a", "b", 1)
    dist = run_sssp(g, "s")
    assert dist["s"] == 0
    assert dist["a"] == 1
    assert math.isinf(dist["b"])
