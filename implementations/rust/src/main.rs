use bmssp::{run_sssp, Graph};

fn main() {
    let mut g = Graph::new();
    g.add_edge("s", "a", 1.0);
    g.add_edge("s", "b", 4.0);
    g.add_edge("a", "b", 2.0);
    g.add_edge("a", "c", 5.0);
    g.add_edge("b", "c", 1.0);
    let dist = run_sssp(&g, "s", false);
    println!("Distances from s: {:?}", dist);
}
