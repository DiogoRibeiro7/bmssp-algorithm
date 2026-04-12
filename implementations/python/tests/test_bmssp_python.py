"""Tests for the Python BMSSP implementation."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make the parent directory importable
IMPL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPL_DIR))

import bmssp as bm  # noqa: E402

SAMPLE_DOT = IMPL_DIR.parents[1] / "docs" / "examples" / "sample.dot"


# ---------- Graph tests ----------


def test_graph_add_edge_creates_nodes():
    g = bm.Graph()
    g.add_edge("a", "b", 1.0)
    assert g.n == 2
    assert "a" in g.name_to_idx
    assert "b" in g.name_to_idx


def test_graph_negative_weight_rejected():
    g = bm.Graph()
    with pytest.raises(ValueError):
        g.add_edge("a", "b", -1.0)


def test_graph_neighbors():
    g = bm.Graph()
    g.add_edge("a", "b", 1.0)
    g.add_edge("a", "c", 2.0)
    a_idx = g.name_to_idx["a"]
    neighbors = g.neighbors(a_idx)
    assert len(neighbors) == 2
    targets = {g.names[n] for n, _ in neighbors}
    assert targets == {"b", "c"}


# ---------- DQueue tests ----------


def test_dqueue_insert_respects_bound():
    dq = bm.DQueue(M=10, B=5.0)
    dq.insert(0, 3.0)
    dq.insert(1, 7.0)  # above bound, ignored
    assert dq.non_empty()
    bi, nodes = dq.pull()
    assert nodes == {0}


def test_dqueue_pull_orders_by_distance():
    dq = bm.DQueue(M=3, B=100.0)
    dq.insert(2, 9.0)
    dq.insert(0, 1.0)
    dq.insert(1, 5.0)
    bi, nodes = dq.pull()
    assert bi == 1.0
    assert nodes == {0, 1, 2}


def test_dqueue_batch_prepend_priority():
    dq = bm.DQueue(M=2, B=100.0)
    dq.insert(0, 1.0)
    dq.batch_prepend([(99, 50.0)])
    bi, nodes = dq.pull()
    # Prepend takes priority even though it has larger distance
    assert 99 in nodes


def test_dqueue_empty_pull():
    dq = bm.DQueue(M=10, B=100.0)
    assert not dq.non_empty()
    bi, nodes = dq.pull()
    assert nodes == set()
    assert bi == 100.0


# ---------- SSSP tests ----------


def test_dijkstra_basic():
    g = bm.Graph()
    g.add_edge("s", "a", 1.0)
    g.add_edge("s", "b", 4.0)
    g.add_edge("a", "b", 2.0)
    g.add_edge("a", "c", 5.0)
    g.add_edge("b", "c", 1.0)
    distances = bm.dijkstra(g, "s")
    assert distances["s"] == 0
    assert distances["a"] == 1
    assert distances["b"] == 3
    assert distances["c"] == 4


def test_run_sssp_returns_dict():
    g = bm.Graph()
    g.add_edge("a", "b", 5.0)
    result = bm.run_sssp(g, "a")
    assert isinstance(result, dict)
    assert result["a"] == 0


def test_dijkstra_unreachable():
    g = bm.Graph()
    g.add_edge("a", "b", 1.0)
    g.add_node("c")
    distances = bm.dijkstra(g, "a")
    assert distances["c"] == float("inf")


def test_zero_weight_edges():
    g = bm.Graph()
    g.add_edge("s", "a", 0.0)
    g.add_edge("a", "b", 0.0)
    distances = bm.dijkstra(g, "s")
    assert distances == {"s": 0, "a": 0, "b": 0}


def test_linear_path():
    g = bm.Graph()
    g.add_edge("a", "b", 1.0)
    g.add_edge("b", "c", 2.0)
    g.add_edge("c", "d", 3.0)
    distances = bm.dijkstra(g, "a")
    assert distances == {"a": 0, "b": 1, "c": 3, "d": 6}


# ---------- DOT parsing tests ----------


def test_load_sample_dot():
    g = bm.load_graph_from_dot(str(SAMPLE_DOT))
    assert g.n == 8
    assert "A" in g.name_to_idx
    assert "H" in g.name_to_idx


def test_sample_dot_correct_distances():
    g = bm.load_graph_from_dot(str(SAMPLE_DOT))
    distances = bm.dijkstra(g, "A")
    assert distances["A"] == 0
    assert distances["B"] == 3
    assert distances["C"] == 6
    assert distances["D"] == 7
    assert distances["E"] == 9
    assert distances["F"] == 10
    assert distances["G"] == 16
    assert distances["H"] == 12


def test_load_missing_file():
    with pytest.raises(RuntimeError, match="cannot open"):
        bm.load_graph_from_dot("/nonexistent.dot")


def test_load_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
        f.write("digraph G {\n}\n")
        path = f.name
    try:
        with pytest.raises(RuntimeError, match="did not contain any nodes"):
            bm.load_graph_from_dot(path)
    finally:
        os.unlink(path)


# ---------- CLI tests ----------


def test_cli_version(capsys):
    code = bm.main(["-V"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Python" in out and "0.1.0" in out


def test_cli_distances(capsys):
    code = bm.main([str(SAMPLE_DOT), "A"])
    assert code == 0
    lines = capsys.readouterr().out.strip().split("\n")
    distances = dict(line.split("\t") for line in lines)
    assert distances["A"] == "0"
    assert distances["H"] == "12"


def test_cli_target_path(capsys):
    code = bm.main([str(SAMPLE_DOT), "A", "C"])
    assert code == 0
    out = capsys.readouterr().out
    assert "A -> C" in out
    assert "distance: 6" in out


def test_cli_json_output(capsys):
    code = bm.main(["--json", str(SAMPLE_DOT), "A"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["source"] == "A"
    assert data["distances"]["H"] == 12


def test_cli_invalid_args(capsys):
    code = bm.main([])
    assert code == 2
