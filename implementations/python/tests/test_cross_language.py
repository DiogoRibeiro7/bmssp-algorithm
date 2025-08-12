import os
import sys
import math
import subprocess
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from bmssp import Graph, run_sssp


def _run_c_graph(tmp_path, n_nodes, edges):
    """Compile bmssp.c with a custom graph and return distances."""
    repo_root = Path(__file__).resolve().parents[3]
    c_src = repo_root / "implementations" / "c" / "bmssp.c"
    c_prog = tmp_path / "custom.c"
    edge_code = "".join(f"    add_edge(g, {u}, {v}, {w});\n" for u, v, w in edges)
    c_prog.write_text(
        f"#define main bmssp_unused_main\n#include \"{c_src}\"\n#undef main\n"
        "int main(){\n"
        f"    Graph *g = new_graph({n_nodes});\n"
        f"{edge_code}    double dist[{n_nodes}];\n"
        f"    run_sssp(g, 0, dist, 0);\n"
        f"    for(int i=0;i<{n_nodes};i++){{\n"
        "        if(dist[i]==INF) printf(\"inf\\n\");\n"
        "        else printf(\"%g\\n\", dist[i]);\n"
        "    }\n    return 0;\n}\n"
    )
    exe = tmp_path / "custom"
    subprocess.check_call(["gcc", str(c_prog), "-lm", "-o", str(exe)])
    output = subprocess.check_output([str(exe)], text=True).splitlines()
    return [float("inf") if line.strip().lower().startswith("inf") else float(line.strip()) for line in output]


def test_python_matches_c(tmp_path):
    g = Graph()
    g.add_edge("s", "a", 1)
    g.add_edge("s", "b", 4)
    g.add_edge("a", "b", 2)
    g.add_edge("a", "c", 5)
    g.add_edge("b", "c", 1)
    py_dist = run_sssp(g, "s")

    repo_root = Path(__file__).resolve().parents[3]
    c_src = repo_root / "implementations" / "c" / "bmssp.c"
    c_exe = tmp_path / "bmssp"
    subprocess.check_call(["gcc", str(c_src), "-lm", "-o", str(c_exe)])
    output = subprocess.check_output([str(c_exe)], text=True).splitlines()
    mapping = {0: "s", 1: "a", 2: "b", 3: "c"}
    c_dist = {}
    for idx, line in enumerate(output):
        val = float('inf') if line.strip().lower().startswith('inf') else float(line.strip())
        c_dist[mapping[idx]] = val

    for node, d in py_dist.items():
        cd = c_dist[node]
        if math.isinf(d):
            assert math.isinf(cd)
        else:
            assert abs(d - cd) < 1e-9


def test_single_vertex_matches_c(tmp_path):
    g = Graph()
    g.add_edge("A", "A", 0)
    py_dist = run_sssp(g, "A")
    c_dist = _run_c_graph(tmp_path, 1, [(0, 0, 0)])
    assert abs(py_dist["A"] - c_dist[0]) < 1e-9


def test_disconnected_graph_matches_c(tmp_path):
    g = Graph()
    g.add_edge("s", "a", 1)
    g.adj.setdefault("b", [])
    py_dist = run_sssp(g, "s")
    c_dist = _run_c_graph(tmp_path, 3, [(0, 1, 1)])
    mapping = {0: "s", 1: "a", 2: "b"}
    for idx, node in mapping.items():
        d = py_dist[node]
        cd = c_dist[idx]
        if math.isinf(d):
            assert math.isinf(cd)
        else:
            assert abs(d - cd) < 1e-9
