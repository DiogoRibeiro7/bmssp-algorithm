"""Tests for the C++ BMSSP implementation via the CLI."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

IMPL_DIR = Path(__file__).resolve().parents[1]
BIN = IMPL_DIR / ("bmssp.exe" if os.name == "nt" else "bmssp")
SAMPLE_DOT = IMPL_DIR.parents[1] / "docs" / "examples" / "sample.dot"


@pytest.fixture(scope="module", autouse=True)
def build_binary():
    """Build the C++ binary once per test session."""
    cxx = shutil.which("g++") or shutil.which("clang++")
    if cxx is None:
        pytest.skip("No C++ compiler found")
    result = subprocess.run(
        [cxx, "-Wall", "-Wextra", "-std=c++17", "-O2", "bmssp.cpp", "-o", BIN.name],
        cwd=IMPL_DIR, capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Build failed: {result.stderr}")
    yield
    if BIN.exists():
        BIN.unlink()


def run_bmssp(*args):
    result = subprocess.run([str(BIN), *args], capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_version():
    code, out, _ = run_bmssp("-V")
    assert code == 0
    assert "C++" in out
    assert "0.1.0" in out


def test_sample_graph_distances():
    """The sample graph from docs has known distances from A."""
    code, out, _ = run_bmssp(str(SAMPLE_DOT), "A")
    assert code == 0
    lines = out.strip().split("\n")
    distances = {}
    for line in lines:
        name, val = line.split("\t")
        distances[name] = val

    expected = {"A": "0", "B": "3", "C": "6", "D": "7",
                "E": "9", "F": "10", "G": "16", "H": "12"}
    assert distances == expected


def test_target_path():
    code, out, _ = run_bmssp(str(SAMPLE_DOT), "A", "C")
    assert code == 0
    assert "A -> C" in out
    assert "distance: 6" in out


def test_unreachable_target():
    """Create a graph with disconnected target."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
        f.write("digraph G {\n  A -> B [label=1];\n  C -> D [label=2];\n}\n")
        path = f.name
    try:
        code, out, _ = run_bmssp(path, "A", "C")
        assert code == 0
        assert "no path" in out
    finally:
        os.unlink(path)


def test_json_output():
    code, out, _ = run_bmssp("--json", str(SAMPLE_DOT), "A")
    assert code == 0
    import json
    data = json.loads(out)
    assert data["source"] == "A"
    assert data["distances"]["A"] == 0
    assert data["distances"]["B"] == 3
    assert data["distances"]["H"] == 12


def test_invalid_args():
    code, _, _ = run_bmssp()
    assert code == 2


def test_missing_source():
    code, _, err = run_bmssp(str(SAMPLE_DOT), "Z")
    assert code == 1
    assert "not found" in err


def test_missing_file():
    code, _, err = run_bmssp("/nonexistent.dot", "A")
    assert code == 1
    assert "cannot open" in err
