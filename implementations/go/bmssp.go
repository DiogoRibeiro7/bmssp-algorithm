package bmssp

import (
	"container/heap"
	"fmt"
	"math"
	"sort"
)

// -------- Graph --------
type Edge struct {
	To string
	W  float64
}

type Graph struct {
	Adj map[string][]Edge
}

func NewGraph() *Graph {
	return &Graph{Adj: make(map[string][]Edge)}
}

func (g *Graph) AddEdge(u, v string, w float64) {
	if w < 0 {
		panic("Only non-negative weights allowed")
	}
	g.Adj[u] = append(g.Adj[u], Edge{v, w})
	if _, ok := g.Adj[v]; !ok {
		g.Adj[v] = []Edge{}
	}
}

func (g *Graph) Neighbors(u string) []Edge {
	return g.Adj[u]
}

// -------- DQueue from Lemma 3.3 --------
type nodeDist struct {
	dist float64
	node string
}

type nodeDistHeap []nodeDist

func (h nodeDistHeap) Len() int           { return len(h) }
func (h nodeDistHeap) Less(i, j int) bool { return h[i].dist < h[j].dist }
func (h nodeDistHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *nodeDistHeap) Push(x any)        { *h = append(*h, x.(nodeDist)) }
func (h *nodeDistHeap) Pop() any {
	old := *h
	n := len(old)
	x := old[n-1]
	*h = old[:n-1]
	return x
}

type DQueue struct {
	M       int
	B       float64
	data    nodeDistHeap
	prepend []nodeDist
}

func NewDQueue(M int, B float64) *DQueue {
	h := nodeDistHeap{}
	heap.Init(&h)
	return &DQueue{M: M, B: B, data: h, prepend: []nodeDist{}}
}

func (dq *DQueue) Insert(node string, dist float64) {
	if dist >= dq.B {
		return
	}
	heap.Push(&dq.data, nodeDist{dist, node})
}

func (dq *DQueue) BatchPrepend(items []nodeDist) {
	for _, it := range items {
		if it.dist < dq.B {
			dq.prepend = append(dq.prepend, it)
		}
	}
	sort.Slice(dq.prepend, func(i, j int) bool { return dq.prepend[i].dist < dq.prepend[j].dist })
}

func (dq *DQueue) Pull() (float64, map[string]struct{}) {
	if len(dq.prepend) > 0 {
		group := dq.prepend
		if len(group) > dq.M {
			group = group[:dq.M]
			dq.prepend = dq.prepend[dq.M:]
		} else {
			dq.prepend = []nodeDist{}
		}
		B_i := dq.B
		if len(group) > 0 {
			B_i = group[0].dist
		}
		nodes := make(map[string]struct{})
		for _, nd := range group {
			nodes[nd.node] = struct{}{}
		}
		return B_i, nodes
	}

	if dq.data.Len() == 0 {
		return dq.B, map[string]struct{}{}
	}

	out := []nodeDist{}
	for dq.data.Len() > 0 && len(out) < dq.M {
		nd := heap.Pop(&dq.data).(nodeDist)
		out = append(out, nd)
	}
	B_i := dq.B
	if len(out) > 0 {
		B_i = out[0].dist
	}
	nodes := make(map[string]struct{})
	for _, nd := range out {
		nodes[nd.node] = struct{}{}
	}
	return B_i, nodes
}

func (dq *DQueue) NonEmpty() bool {
	return dq.data.Len() > 0 || len(dq.prepend) > 0
}

// -------- Helper functions --------
func setUnion(a, b map[string]struct{}) map[string]struct{} {
	out := make(map[string]struct{})
	for k := range a {
		out[k] = struct{}{}
	}
	for k := range b {
		out[k] = struct{}{}
	}
	return out
}

func setCopy(a map[string]struct{}) map[string]struct{} {
	out := make(map[string]struct{})
	for k := range a {
		out[k] = struct{}{}
	}
	return out
}

// -------- Result containers for API consistency --------

// PivotResult mirrors the cross-language API structure by bundling
// the set of pivot nodes `P` and all visited nodes `W`.
type PivotResult struct {
	P map[string]struct{}
	W map[string]struct{}
}

// BaseCaseResult stores the updated bound `B` and the subset `U` of
// nodes whose shortest paths are finalized in the base case.
type BaseCaseResult struct {
	B float64
	U map[string]struct{}
}

// BMSSPResult is returned by the recursive BMSSP routine, carrying the
// new bound and set of completed nodes from that invocation.
type BMSSPResult struct {
	B float64
	U map[string]struct{}
}

// -------- Algorithm 1: FindPivots --------
func FindPivots(
	graph *Graph,
	B float64,
	S map[string]struct{},
	dHat map[string]float64,
	complete map[string]struct{},
	k int,
	verbose bool,
) PivotResult {
	W := setCopy(S)
	Wprev := setCopy(S)
	if verbose {
		fmt.Printf("find_pivots: start |S|=%d B=%g\n", len(S), B)
	}

	for i := 1; i <= k; i++ {
		Wi := make(map[string]struct{})
		for u := range Wprev {
			du := dHat[u]
			if du >= B {
				continue
			}
			for _, e := range graph.Neighbors(u) {
				if du+e.W <= dHat[e.To] {
					dHat[e.To] = du + e.W
					if du+e.W < B {
						Wi[e.To] = struct{}{}
					}
				}
			}
		}
		for v := range Wi {
			W[v] = struct{}{}
		}
		if len(W) > k*len(S) {
			if verbose {
				fmt.Println("find_pivots: early termination |W| > k*|S|")
			}
			return PivotResult{P: setCopy(S), W: W}
		}
		Wprev = Wi
	}

	FChildren := make(map[string][]string)
	indeg := make(map[string]int)
	for u := range W {
		indeg[u] = 0
	}
	for u := range W {
		du := dHat[u]
		for _, e := range graph.Neighbors(u) {
			if _, ok := W[e.To]; ok && math.Abs(dHat[e.To]-(du+e.W)) < 1e-12 {
				FChildren[u] = append(FChildren[u], e.To)
				indeg[e.To]++
			}
		}
	}

	var subtreeSize func(string) int
	subtreeSize = func(u string) int {
		size := 1
		for _, child := range FChildren[u] {
			size += subtreeSize(child)
		}
		return size
	}

	P := make(map[string]struct{})
	for u := range S {
		if indeg[u] == 0 && subtreeSize(u) >= k {
			P[u] = struct{}{}
		}
	}
	if verbose {
		fmt.Print("find_pivots: pivots={")
		first := true
		for u := range P {
			if !first {
				fmt.Print(", ")
			}
			fmt.Print(u)
			first = false
		}
		fmt.Println("}")
	}
	return PivotResult{P: P, W: W}
}

// -------- Algorithm 2: BaseCase --------
func BaseCase(
	graph *Graph,
	B float64,
	S map[string]struct{},
	dHat map[string]float64,
	complete map[string]struct{},
	k int,
	verbose bool,
) BaseCaseResult {
	var x string
	for u := range S {
		x = u
		break
	}
	U0 := map[string]struct{}{x: {}}
	H := &nodeDistHeap{}
	heap.Init(H)
	heap.Push(H, nodeDist{dHat[x], x})
	visited := make(map[string]struct{})
	if verbose {
		fmt.Printf("base_case: start from %s with B=%g\n", x, B)
	}

	for H.Len() > 0 && len(U0) < k+1 {
		nd := heap.Pop(H).(nodeDist)
		du, u := nd.dist, nd.node
		if _, ok := visited[u]; ok {
			continue
		}
		visited[u] = struct{}{}
		U0[u] = struct{}{}
		complete[u] = struct{}{}
		for _, e := range graph.Neighbors(u) {
			if du+e.W <= dHat[e.To] && du+e.W < B {
				dHat[e.To] = du + e.W
				heap.Push(H, nodeDist{dHat[e.To], e.To})
			}
		}
	}

	if len(U0) <= k {
		if verbose {
			fmt.Println("base_case: early termination |U0| <= k")
		}
		return BaseCaseResult{B: B, U: U0}
	}
	Bprime := math.Inf(-1)
	for v := range U0 {
		if dHat[v] > Bprime {
			Bprime = dHat[v]
		}
	}
	if verbose {
		fmt.Printf("base_case: computed B'=%g\n", Bprime)
	}
	U := make(map[string]struct{})
	for v := range U0 {
		if dHat[v] < Bprime {
			U[v] = struct{}{}
		}
	}
	return BaseCaseResult{B: Bprime, U: U}
}

// -------- Algorithm 3: BMSSP --------
func BMSSP(
	graph *Graph,
	l int,
	B float64,
	S map[string]struct{},
	dHat map[string]float64,
	complete map[string]struct{},
	k int,
	t int,
	verbose bool,
) BMSSPResult {
	if verbose {
		fmt.Printf("bmssp: level=%d B=%g |S|=%d\n", l, B, len(S))
	}
	if l == 0 {
		bc := BaseCase(graph, B, S, dHat, complete, k, verbose)
		if verbose {
			fmt.Printf("bmssp: base case returns B=%g |U|=%d\n", bc.B, len(bc.U))
		}
		return BMSSPResult{B: bc.B, U: bc.U}
	}

	piv := FindPivots(graph, B, S, dHat, complete, k, verbose)
	P, W := piv.P, piv.W
	if verbose {
		fmt.Print("bmssp: pivots={")
		first := true
		for x := range P {
			if !first {
				fmt.Print(", ")
			}
			fmt.Print(x)
			first = false
		}
		fmt.Println("}")
	}
	M := 1 << ((l - 1) * t)
	D := NewDQueue(M, B)
	for x := range P {
		D.Insert(x, dHat[x])
	}
	U := make(map[string]struct{})
	B0prime := B
	for x := range P {
		if dHat[x] < B0prime {
			B0prime = dHat[x]
		}
	}
	if verbose {
		fmt.Printf("bmssp: B0'=%g\n", B0prime)
	}

	for len(U) < k*(1<<(l*t)) && D.NonEmpty() {
		Bi, Si := D.Pull()
		rec := BMSSP(graph, l-1, Bi, Si, dHat, complete, k, t, verbose)
		Bprimei, Ui := rec.B, rec.U
		for u := range Ui {
			U[u] = struct{}{}
		}
		K := []nodeDist{}
		for u := range Ui {
			for _, e := range graph.Neighbors(u) {
				if dHat[u]+e.W <= dHat[e.To] {
					dHat[e.To] = dHat[u] + e.W
					if Bi <= dHat[e.To] && dHat[e.To] < B {
						D.Insert(e.To, dHat[e.To])
					} else if Bprimei <= dHat[e.To] && dHat[e.To] < Bi {
						K = append(K, nodeDist{dHat[e.To], e.To})
					}
				}
			}
		}
		prependItems := append([]nodeDist{}, K...)
		for x := range Si {
			if dist := dHat[x]; Bprimei <= dist && dist < Bi {
				prependItems = append(prependItems, nodeDist{dist, x})
			}
		}
		D.BatchPrepend(prependItems)
	}
	if verbose {
		reason := "condition"
		if len(U) >= k*(1<<(l*t)) {
			reason = "U size reached"
		} else if !D.NonEmpty() {
			reason = "queue empty"
		}
		fmt.Println("bmssp: terminating loop due to", reason)
	}

	Bprime := B0prime
	if Bprime > B {
		Bprime = B
	}
	for x := range W {
		if dHat[x] < Bprime {
			U[x] = struct{}{}
		}
	}
	for u := range U {
		complete[u] = struct{}{}
	}
	if verbose {
		fmt.Printf("bmssp: returning B=%g |U|=%d\n", Bprime, len(U))
	}
	return BMSSPResult{B: Bprime, U: U}
}

// -------- Main Driver --------
func RunSSSP(graph *Graph, source string, verbose bool) map[string]float64 {
	n := len(graph.Adj)
	k := int(math.Max(1, math.Pow(math.Log2(float64(n)), 1.0/3.0)))
	t := int(math.Max(1, math.Pow(math.Log2(float64(n)), 2.0/3.0)))
	l := int(math.Ceil(math.Log2(float64(n)) / float64(t)))

	dHat := make(map[string]float64)
	for v := range graph.Adj {
		dHat[v] = math.Inf(1)
	}
	dHat[source] = 0.0
	complete := map[string]struct{}{source: {}}

	_ = BMSSP(graph, l, math.Inf(1), map[string]struct{}{source: {}}, dHat, complete, k, t, verbose)
	return dHat
}

// -------- Example --------
func main() {
	g := NewGraph()
	g.AddEdge("s", "a", 1)
	g.AddEdge("s", "b", 4)
	g.AddEdge("a", "b", 2)
	g.AddEdge("a", "c", 5)
	g.AddEdge("b", "c", 1)
	dist := RunSSSP(g, "s", false)
	fmt.Println("Distances from s:", dist)
}
