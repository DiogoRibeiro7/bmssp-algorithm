package bmssp

import (
	"fmt"
	"math/rand"
	"testing"
)

// ---- Graph generators ----

func genSparse(n, edgeFactor int) *Graph {
	g := NewGraph()
	r := rand.New(rand.NewSource(42))
	for i := 0; i < n; i++ {
		g.Adj[fmt.Sprintf("n%d", i)] = []Edge{}
	}
	m := edgeFactor * n
	for i := 0; i < m; i++ {
		u := r.Intn(n)
		v := r.Intn(n)
		if u == v {
			continue
		}
		g.AddEdge(fmt.Sprintf("n%d", u), fmt.Sprintf("n%d", v), float64(r.Intn(100)+1))
	}
	return g
}

func genGrid(w, h int) *Graph {
	g := NewGraph()
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			u := fmt.Sprintf("v%d_%d", x, y)
			if x+1 < w {
				g.AddEdge(u, fmt.Sprintf("v%d_%d", x+1, y), 1.0)
			}
			if y+1 < h {
				g.AddEdge(u, fmt.Sprintf("v%d_%d", x, y+1), 1.0)
			}
		}
	}
	return g
}

// ---- SSSP benchmarks ----

func BenchmarkRunSSSP_Sparse_100(b *testing.B)   { benchRunSSSP(b, genSparse(100, 3)) }
func BenchmarkRunSSSP_Sparse_1000(b *testing.B)  { benchRunSSSP(b, genSparse(1000, 3)) }
func BenchmarkRunSSSP_Sparse_10000(b *testing.B) { benchRunSSSP(b, genSparse(10000, 3)) }

func BenchmarkRunSSSP_Grid_10x10(b *testing.B)   { benchRunSSSP(b, genGrid(10, 10)) }
func BenchmarkRunSSSP_Grid_50x50(b *testing.B)   { benchRunSSSP(b, genGrid(50, 50)) }
func BenchmarkRunSSSP_Grid_100x100(b *testing.B) { benchRunSSSP(b, genGrid(100, 100)) }

func benchRunSSSP(b *testing.B, g *Graph) {
	var source string
	for k := range g.Adj {
		source = k
		break
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		RunSSSP(g, source, false)
	}
}

// ---- DQueue micro-benchmarks ----

func BenchmarkDQueueInsert(b *testing.B) {
	dq := NewDQueue(100, 1e9)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		dq.Insert(fmt.Sprintf("n%d", i), float64(i))
	}
}

func BenchmarkDQueuePull(b *testing.B) {
	b.StopTimer()
	for i := 0; i < b.N; i++ {
		dq := NewDQueue(16, 1e9)
		for j := 0; j < 64; j++ {
			dq.Insert(fmt.Sprintf("n%d", j), float64(j))
		}
		b.StartTimer()
		dq.Pull()
		b.StopTimer()
	}
}
