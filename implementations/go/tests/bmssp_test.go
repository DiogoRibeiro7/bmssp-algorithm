package bmssp_test

import (
    "bmssp"
    "math"
    "testing"
)

func TestRunSSSP(t *testing.T) {
    g := bmssp.NewGraph()
    g.AddEdge("s", "a", 1)
    g.AddEdge("s", "b", 4)
    g.AddEdge("a", "b", 2)
    g.AddEdge("a", "c", 5)
    g.AddEdge("b", "c", 1)
    dist := bmssp.RunSSSP(g, "s", false)
    if dist["s"] != 0 || dist["a"] != 1 || dist["b"] != 4 || !math.IsInf(dist["c"], 1) {
        t.Fatalf("unexpected distances: %v", dist)
    }
}

func TestSingleVertex(t *testing.T) {
    g := bmssp.NewGraph()
    g.Adj["s"] = []bmssp.Edge{}
    dist := bmssp.RunSSSP(g, "s", false)
    if dist["s"] != 0 {
        t.Fatalf("expected 0, got %v", dist["s"])
    }
}

func TestDisconnectedGraph(t *testing.T) {
    g := bmssp.NewGraph()
    g.AddEdge("s", "a", 1)
    g.Adj["b"] = []bmssp.Edge{}
    dist := bmssp.RunSSSP(g, "s", false)
    if dist["a"] != 1 || !math.IsInf(dist["b"], 1) {
        t.Fatalf("unexpected distances: %v", dist)
    }
}
