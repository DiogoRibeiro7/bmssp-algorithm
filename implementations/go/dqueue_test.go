package bmssp

import "testing"

func TestDQueuePullOrdersPrepend(t *testing.T) {
	dq := NewDQueue(2, 10)
	items := []nodeDist{{dist: 5, node: "x"}, {dist: 1, node: "y"}, {dist: 3, node: "z"}}
	dq.BatchPrepend(items)
	Bi, nodes := dq.Pull()
	if Bi != 1 {
		t.Fatalf("expected Bi=1 got %v", Bi)
	}
	if len(nodes) != 2 {
		t.Fatalf("expected 2 nodes, got %d", len(nodes))
	}
	if _, ok := nodes["y"]; !ok {
		t.Fatalf("expected node y in result")
	}
	if _, ok := nodes["z"]; !ok {
		t.Fatalf("expected node z in result")
	}
}
