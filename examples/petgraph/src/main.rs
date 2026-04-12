//! petgraph integration example for BMSSP.
//!
//! Shows how to convert a `petgraph::Graph<&str, f64, Directed>` into the
//! BMSSP `Graph` type and run shortest paths.
//!
//! Run with:
//!     cargo run --release

use bmssp::{run_sssp, Graph as BmsspGraph};
use petgraph::algo::dijkstra;
use petgraph::graph::{DiGraph, NodeIndex};
use std::collections::HashMap;

/// Convert a petgraph DiGraph with string node weights and f64 edge weights
/// into a BMSSP Graph. Uses node weights as the BMSSP node names.
fn from_petgraph(g: &DiGraph<&str, f64>) -> (BmsspGraph, HashMap<NodeIndex, String>) {
    let mut bg = BmsspGraph::new();
    let mut idx_to_name = HashMap::new();
    for ni in g.node_indices() {
        let name = g[ni].to_string();
        idx_to_name.insert(ni, name.clone());
    }
    for ei in g.edge_indices() {
        let (u, v) = g.edge_endpoints(ei).unwrap();
        let w = *g.edge_weight(ei).unwrap();
        bg.add_edge(&idx_to_name[&u], &idx_to_name[&v], w);
    }
    (bg, idx_to_name)
}

fn main() {
    println!("=================================================");
    println!("petgraph -> BMSSP integration example");
    println!("=================================================");

    // Build a small road-network-like graph
    let mut g: DiGraph<&str, f64> = DiGraph::new();
    let home = g.add_node("Home");
    let bakery = g.add_node("Bakery");
    let school = g.add_node("School");
    let market = g.add_node("Market");
    let library = g.add_node("Library");
    let park = g.add_node("Park");

    g.add_edge(home, bakery, 2.0);
    g.add_edge(home, school, 5.0);
    g.add_edge(bakery, school, 1.0);
    g.add_edge(bakery, market, 4.0);
    g.add_edge(school, library, 3.0);
    g.add_edge(market, library, 2.0);
    g.add_edge(library, park, 6.0);
    g.add_edge(school, park, 8.0);

    // petgraph baseline
    let pg_dist = dijkstra(&g, home, None, |e| *e.weight());

    // Convert to BMSSP and run
    let (bg, idx_to_name) = from_petgraph(&g);
    let bm_dist = run_sssp(&bg, "Home", false);

    println!("\nDistances from 'Home':");
    println!("{:<10}{:<12}{:<12}{:<8}", "node", "petgraph", "bmssp", "match");
    println!("{}", "-".repeat(42));

    let mut nodes: Vec<NodeIndex> = g.node_indices().collect();
    nodes.sort_by_key(|n| g[*n].to_string());
    for ni in nodes {
        let name = &idx_to_name[&ni];
        let pg = pg_dist.get(&ni).copied().unwrap_or(f64::INFINITY);
        let bm = bm_dist.get(name).copied().unwrap_or(f64::INFINITY);
        let matched = if (pg - bm).abs() < 1e-9 || (pg.is_infinite() && bm.is_infinite()) {
            "yes"
        } else {
            "NO"
        };
        println!("{:<10}{:<12}{:<12}{:<8}", name, pg, bm, matched);
    }
}
