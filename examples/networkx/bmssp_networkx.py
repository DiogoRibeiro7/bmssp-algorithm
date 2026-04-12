"""
NetworkX integration example for BMSSP.

This module shows how to convert a NetworkX DiGraph to the BMSSP Graph type
and run shortest paths using the Python BMSSP implementation.

Usage:
    python bmssp_networkx.py

Requirements:
    - networkx
    - numpy, scipy (for the BMSSP implementation)
"""

import sys
from pathlib import Path

# Make the BMSSP Python implementation importable
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementations" / "python"))

import networkx as nx
import bmssp as bm


def from_networkx(G: nx.DiGraph, weight_attr: str = "weight") -> bm.Graph:
    """Convert a NetworkX DiGraph to a BMSSP Graph.

    Node identities become string names (via str(node)).
    Edge weights are read from the given attribute (default: 'weight').
    Missing weight attributes default to 1.0.
    """
    g = bm.Graph()
    for node in G.nodes():
        g.add_node(str(node))
    for u, v, data in G.edges(data=True):
        w = float(data.get(weight_attr, 1.0))
        g.add_edge(str(u), str(v), w)
    return g


def shortest_path_lengths(G: nx.DiGraph, source, weight_attr: str = "weight"):
    """Compute single-source shortest path lengths via BMSSP/Dijkstra.

    Returns a dict {node: distance} matching nx.single_source_dijkstra_path_length.
    """
    bg = from_networkx(G, weight_attr)
    distances = bm.dijkstra(bg, str(source))
    return {n: d for n, d in distances.items()}


def example_road_network():
    """Build a small road-network-like graph and compare with NetworkX Dijkstra."""
    G = nx.DiGraph()
    edges = [
        ("Home", "Bakery", 2),
        ("Home", "School", 5),
        ("Bakery", "School", 1),
        ("Bakery", "Market", 4),
        ("School", "Library", 3),
        ("Market", "Library", 2),
        ("Library", "Park", 6),
        ("School", "Park", 8),
    ]
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)

    # NetworkX baseline
    nx_dist = nx.single_source_dijkstra_path_length(G, "Home")

    # BMSSP via the adapter
    bm_dist = shortest_path_lengths(G, "Home")

    print("Distances from 'Home':")
    print(f"{'node':<10}{'networkx':<12}{'bmssp':<12}{'match':<8}")
    print("-" * 42)
    for node in sorted(G.nodes()):
        nx_d = nx_dist.get(node, float("inf"))
        bm_d = bm_dist.get(node, float("inf"))
        match = "yes" if abs(nx_d - bm_d) < 1e-9 else "NO"
        print(f"{node:<10}{nx_d:<12}{bm_d:<12}{match:<8}")


def example_random_graph(n=20, seed=42):
    """Generate a random sparse graph with NetworkX, run BMSSP via the adapter."""
    G = nx.gnp_random_graph(n, 0.15, directed=True, seed=seed)
    import random
    random.seed(seed)
    for u, v in G.edges():
        G[u][v]["weight"] = random.randint(1, 10)

    print(f"\nRandom graph: {n} nodes, {G.number_of_edges()} edges")
    bm_dist = shortest_path_lengths(G, 0)
    nx_dist = nx.single_source_dijkstra_path_length(G, 0)

    import math
    def equal(a, b):
        if math.isinf(a) and math.isinf(b): return True
        return abs(a - b) < 1e-9
    matches = sum(1 for n in G.nodes() if equal(bm_dist[str(n)], nx_dist.get(n, float("inf"))))
    print(f"  Matched {matches}/{n} distances with NetworkX baseline")


if __name__ == "__main__":
    print("=" * 50)
    print("NetworkX -> BMSSP integration example")
    print("=" * 50)
    example_road_network()
    example_random_graph()
