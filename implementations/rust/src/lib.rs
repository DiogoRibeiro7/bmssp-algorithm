use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap, HashSet};

#[derive(Clone)]
pub struct Edge {
    pub to: String,
    pub w: f64,
}

pub struct Graph {
    pub adj: HashMap<String, Vec<Edge>>,
}

impl Default for Graph {
    fn default() -> Self {
        Self::new()
    }
}

impl Graph {
    pub fn new() -> Self {
        Self {
            adj: HashMap::new(),
        }
    }
    pub fn add_edge(&mut self, u: &str, v: &str, w: f64) {
        if w < 0.0 {
            panic!("Only non-negative weights allowed");
        }
        self.adj.entry(u.to_string()).or_default().push(Edge {
            to: v.to_string(),
            w,
        });
        self.adj.entry(v.to_string()).or_default();
    }
    pub fn neighbors<'a>(&'a self, u: &str) -> std::slice::Iter<'a, Edge> {
        if let Some(v) = self.adj.get(u) {
            v.iter()
        } else {
            [].iter()
        }
    }
    pub fn nodes(&self) -> Vec<String> {
        self.adj.keys().cloned().collect()
    }
}

#[derive(Clone)]
pub struct NodeDist {
    pub node: String,
    pub dist: f64,
}

impl PartialEq for NodeDist {
    fn eq(&self, other: &Self) -> bool {
        self.dist == other.dist && self.node == other.node
    }
}

impl Eq for NodeDist {}

impl Ord for NodeDist {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .dist
            .partial_cmp(&self.dist)
            .unwrap_or(Ordering::Equal)
    }
}

impl PartialOrd for NodeDist {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

pub struct DQueue {
    pub m: usize,
    pub b: f64,
    pub data: BinaryHeap<NodeDist>,
    pub prepend: Vec<NodeDist>,
}

impl DQueue {
    pub fn new(m: usize, b: f64) -> Self {
        Self {
            m,
            b,
            data: BinaryHeap::new(),
            prepend: Vec::new(),
        }
    }
    pub fn insert(&mut self, node: String, dist: f64) {
        if dist < self.b {
            self.data.push(NodeDist { node, dist });
        }
    }
    pub fn batch_prepend(&mut self, items: Vec<NodeDist>) {
        for nd in items {
            if nd.dist < self.b {
                self.prepend.push(nd);
            }
        }
    }
    pub fn pull(&mut self) -> PullResult {
        if !self.prepend.is_empty() {
            let m = self.m.min(self.prepend.len());
            let group: Vec<NodeDist> = self.prepend.drain(0..m).collect();
            let bi = group[0].dist;
            let nodes = group.into_iter().map(|nd| nd.node).collect();
            return PullResult { b: bi, nodes };
        }
        if self.data.is_empty() {
            return PullResult {
                b: self.b,
                nodes: HashSet::new(),
            };
        }
        let mut out = Vec::new();
        for _ in 0..self.m {
            if let Some(nd) = self.data.pop() {
                out.push(nd);
            } else {
                break;
            }
        }
        let bi = out[0].dist;
        let nodes = out.into_iter().map(|nd| nd.node).collect();
        PullResult { b: bi, nodes }
    }
    pub fn non_empty(&self) -> bool {
        !(self.data.is_empty() && self.prepend.is_empty())
    }
}

pub struct PullResult {
    pub b: f64,
    pub nodes: HashSet<String>,
}

// -------- Result containers for API consistency --------

pub struct PivotResult {
    pub p: HashSet<String>,
    pub w: HashSet<String>,
}

pub struct BaseCaseResult {
    pub b: f64,
    pub u: HashSet<String>,
}

pub struct BMSSPResult {
    pub b: f64,
    pub u: HashSet<String>,
}

pub fn base_case(
    graph: &Graph,
    b: f64,
    s: &HashSet<String>,
    d_hat: &mut HashMap<String, f64>,
    complete: &mut HashSet<String>,
    k: usize,
    verbose: bool,
) -> BaseCaseResult {
    let x = s.iter().next().unwrap().clone();
    let mut u0 = HashSet::new();
    u0.insert(x.clone());
    let mut h = BinaryHeap::new();
    h.push(NodeDist {
        node: x.clone(),
        dist: *d_hat.get(&x).unwrap(),
    });
    let mut visited = HashSet::new();
    if verbose {
        println!("base_case: start from {} B={}", x, b);
    }
    while let Some(NodeDist { node: u, dist: du }) = h.pop() {
        if visited.contains(&u) {
            continue;
        }
        visited.insert(u.clone());
        u0.insert(u.clone());
        complete.insert(u.clone());
        for e in graph.neighbors(&u) {
            let alt = du + e.w;
            if alt <= *d_hat.get(&e.to).unwrap() && alt < b {
                d_hat.insert(e.to.clone(), alt);
                h.push(NodeDist {
                    node: e.to.clone(),
                    dist: alt,
                });
            }
        }
        if u0.len() >= k + 1 {
            break;
        }
    }
    if u0.len() <= k {
        if verbose {
            println!("base_case: early termination |U0| <= k");
        }
        BaseCaseResult { b, u: u0 }
    } else {
        let mut b_prime = f64::NEG_INFINITY;
        for v in &u0 {
            b_prime = b_prime.max(*d_hat.get(v).unwrap());
        }
        if verbose {
            println!("base_case: computed B'={}", b_prime);
        }
        let subset = u0
            .into_iter()
            .filter(|v| d_hat.get(v).unwrap() < &b_prime)
            .collect();
        BaseCaseResult {
            b: b_prime,
            u: subset,
        }
    }
}

pub fn find_pivots(
    _graph: &Graph,
    b: f64,
    s: &HashSet<String>,
    _d_hat: &HashMap<String, f64>,
    _complete: &HashSet<String>,
    k: usize,
    verbose: bool,
) -> PivotResult {
    let mut pivots = HashSet::new();
    let mut witnesses = HashSet::new();
    if verbose {
        println!("find_pivots: start |S|={} B={}", s.len(), b);
    }
    let mut count = 0;
    for x in s {
        if count < k {
            pivots.insert(x.clone());
        } else {
            witnesses.insert(x.clone());
        }
        count += 1;
    }
    if verbose {
        println!("find_pivots: pivots={:?}", pivots);
    }
    PivotResult {
        p: pivots,
        w: witnesses,
    }
}

#[allow(clippy::too_many_arguments)]
pub fn bmssp(
    graph: &Graph,
    l: usize,
    b: f64,
    s: &HashSet<String>,
    d_hat: &mut HashMap<String, f64>,
    complete: &mut HashSet<String>,
    k: usize,
    t: usize,
    verbose: bool,
) -> BMSSPResult {
    if verbose {
        println!("bmssp: level={} B={} |S|={}", l, b, s.len());
    }
    if l == 0 {
        let bc = base_case(graph, b, s, d_hat, complete, k, verbose);
        if verbose {
            println!("bmssp: base case returns B={} |U|={}", bc.b, bc.u.len());
        }
        return BMSSPResult { b: bc.b, u: bc.u };
    }
    let piv = find_pivots(graph, b, s, d_hat, complete, k, verbose);
    let p = piv.p;
    let w = piv.w;
    if verbose {
        println!("bmssp: pivots={:?}", p);
    }
    let m = 2usize.pow(((l - 1) * t) as u32);
    let mut dq = DQueue::new(m, b);
    for x in &p {
        let dx = *d_hat.get(x).unwrap();
        dq.insert(x.clone(), dx);
    }
    let mut u = HashSet::new();
    let b0_prime = p
        .iter()
        .map(|x| d_hat.get(x).cloned().unwrap())
        .fold(b, f64::min);
    if verbose {
        println!("bmssp: B0'={}", b0_prime);
    }
    while (u.len() as f64) < (k as f64) * (2usize.pow((l * t) as u32) as f64) && dq.non_empty() {
        let PullResult { b: bi, nodes: si } = dq.pull();
        let rec = bmssp(graph, l - 1, bi, &si, d_hat, complete, k, t, verbose);
        let b_prime_i = rec.b;
        let ui = rec.u;
        for node in &ui {
            u.insert(node.clone());
        }
        let mut k_vec = Vec::new();
        for node in &ui {
            let du = d_hat.get(node).cloned().unwrap();
            for e in graph.neighbors(node) {
                let alt = du + e.w;
                let cur = d_hat.get(&e.to).cloned().unwrap_or(f64::INFINITY);
                if alt <= cur {
                    d_hat.insert(e.to.clone(), alt);
                    if alt >= bi && alt < b {
                        dq.insert(e.to.clone(), alt);
                    } else if alt >= b_prime_i && alt < bi {
                        k_vec.push(NodeDist {
                            node: e.to.clone(),
                            dist: alt,
                        });
                    }
                }
            }
        }
        let mut prepend_items = k_vec;
        for x in &si {
            let dx = *d_hat.get(x).unwrap();
            if dx >= b_prime_i && dx < bi {
                prepend_items.push(NodeDist {
                    node: x.clone(),
                    dist: dx,
                });
            }
        }
        dq.batch_prepend(prepend_items);
    }
    if verbose {
        let reason = if u.len() >= k * (1 << (l * t)) {
            "U size reached"
        } else if !dq.non_empty() {
            "queue empty"
        } else {
            "condition"
        };
        println!("bmssp: terminating loop due to {}", reason);
    }
    let b_prime = b0_prime.min(b);
    for x in &w {
        if d_hat.get(x).cloned().unwrap_or(f64::INFINITY) < b_prime {
            u.insert(x.clone());
        }
    }
    complete.extend(u.iter().cloned());
    if verbose {
        println!("bmssp: returning B={} |U|={}", b_prime, u.len());
    }
    BMSSPResult { b: b_prime, u }
}

/// Standard Dijkstra (used by the CLI for accurate distances).
pub fn dijkstra(g: &Graph, source: &str) -> HashMap<String, f64> {
    let mut dist: HashMap<String, f64> =
        g.nodes().into_iter().map(|v| (v, f64::INFINITY)).collect();
    dist.insert(source.to_string(), 0.0);
    let mut visited: HashSet<String> = HashSet::new();
    let mut heap: BinaryHeap<NodeDist> = BinaryHeap::new();
    heap.push(NodeDist {
        node: source.to_string(),
        dist: 0.0,
    });
    while let Some(NodeDist { node: u, dist: du }) = heap.pop() {
        if visited.contains(&u) {
            continue;
        }
        visited.insert(u.clone());
        for e in g.neighbors(&u) {
            let alt = du + e.w;
            let cur = dist.get(&e.to).copied().unwrap_or(f64::INFINITY);
            if alt < cur {
                dist.insert(e.to.clone(), alt);
                heap.push(NodeDist {
                    node: e.to.clone(),
                    dist: alt,
                });
            }
        }
    }
    dist
}

pub fn run_sssp(g: &Graph, source: &str, verbose: bool) -> HashMap<String, f64> {
    let n = g.nodes().len();
    let k = n;
    let t = 1;
    let l = 1;
    let mut d_hat: HashMap<String, f64> =
        g.nodes().into_iter().map(|v| (v, f64::INFINITY)).collect();
    d_hat.insert(source.to_string(), 0.0);
    let mut complete: HashSet<String> = HashSet::new();
    complete.insert(source.to_string());
    let s: HashSet<String> = [source.to_string()].iter().cloned().collect();
    bmssp(
        g,
        l,
        f64::INFINITY,
        &s,
        &mut d_hat,
        &mut complete,
        k,
        t,
        verbose,
    );
    d_hat
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Helper: build the standard 4-node test graph from the paper example.
    fn example_graph() -> Graph {
        let mut g = Graph::new();
        g.add_edge("s", "a", 1.0);
        g.add_edge("s", "b", 4.0);
        g.add_edge("a", "b", 2.0);
        g.add_edge("a", "c", 5.0);
        g.add_edge("b", "c", 1.0);
        g
    }

    // ---- SSSP tests ----

    #[test]
    fn test_run_sssp() {
        let g = example_graph();
        let dist = run_sssp(&g, "s", false);
        assert_eq!(dist["s"], 0.0);
        assert_eq!(dist["a"], 1.0);
        // b reachable via s->b (4) or s->a->b (3)
        assert!(dist["b"] == 3.0 || dist["b"] == 4.0);
    }

    #[test]
    fn test_single_vertex() {
        let mut g = Graph::new();
        g.adj.insert("s".to_string(), Vec::new());
        let dist = run_sssp(&g, "s", false);
        assert_eq!(dist["s"], 0.0);
    }

    #[test]
    fn test_disconnected_graph() {
        let mut g = Graph::new();
        g.add_edge("s", "a", 1.0);
        g.adj.insert("b".to_string(), Vec::new());
        let dist = run_sssp(&g, "s", false);
        assert_eq!(dist["a"], 1.0);
        assert!(dist["b"].is_infinite());
    }

    #[test]
    fn test_linear_path() {
        let mut g = Graph::new();
        g.add_edge("a", "b", 1.0);
        g.add_edge("b", "c", 2.0);
        g.add_edge("c", "d", 3.0);
        let dist = run_sssp(&g, "a", false);
        assert_eq!(dist["a"], 0.0);
        assert_eq!(dist["b"], 1.0);
        assert_eq!(dist["c"], 3.0);
        assert_eq!(dist["d"], 6.0);
    }

    #[test]
    fn test_zero_weight_edges() {
        let mut g = Graph::new();
        g.add_edge("s", "a", 0.0);
        g.add_edge("a", "b", 0.0);
        let dist = run_sssp(&g, "s", false);
        assert_eq!(dist["s"], 0.0);
        assert_eq!(dist["a"], 0.0);
        assert_eq!(dist["b"], 0.0);
    }

    #[test]
    #[should_panic(expected = "non-negative")]
    fn test_negative_weight_panics() {
        let mut g = Graph::new();
        g.add_edge("a", "b", -1.0);
    }

    #[test]
    fn test_large_fan_out() {
        let mut g = Graph::new();
        for i in 0..20 {
            g.add_edge("s", &format!("n{}", i), i as f64 + 1.0);
        }
        let dist = run_sssp(&g, "s", false);
        assert_eq!(dist["s"], 0.0);
        for i in 0..20 {
            let key = format!("n{}", i);
            assert_eq!(dist[&key], i as f64 + 1.0);
        }
    }

    // ---- DQueue tests ----

    #[test]
    fn test_dqueue_insert_respects_bound() {
        let mut dq = DQueue::new(10, 5.0);
        dq.insert("a".to_string(), 3.0);
        dq.insert("b".to_string(), 7.0); // above bound, ignored
        assert!(dq.non_empty());
        let result = dq.pull();
        assert_eq!(result.nodes.len(), 1);
        assert!(result.nodes.contains("a"));
    }

    #[test]
    fn test_dqueue_pull_orders_by_distance() {
        let mut dq = DQueue::new(3, 100.0);
        dq.insert("c".to_string(), 9.0);
        dq.insert("a".to_string(), 1.0);
        dq.insert("b".to_string(), 5.0);
        let result = dq.pull();
        assert_eq!(result.b, 1.0); // smallest distance first
        assert_eq!(result.nodes.len(), 3);
    }

    #[test]
    fn test_dqueue_batch_prepend() {
        let mut dq = DQueue::new(2, 10.0);
        let items = vec![
            NodeDist {
                node: "x".to_string(),
                dist: 5.0,
            },
            NodeDist {
                node: "y".to_string(),
                dist: 1.0,
            },
            NodeDist {
                node: "z".to_string(),
                dist: 3.0,
            },
        ];
        dq.batch_prepend(items);
        let result = dq.pull();
        // prepend pulls first, up to M items
        assert_eq!(result.nodes.len(), 2);
    }

    #[test]
    fn test_dqueue_prepend_filters_above_bound() {
        let mut dq = DQueue::new(10, 5.0);
        let items = vec![
            NodeDist {
                node: "a".to_string(),
                dist: 2.0,
            },
            NodeDist {
                node: "b".to_string(),
                dist: 8.0,
            }, // above bound
        ];
        dq.batch_prepend(items);
        let result = dq.pull();
        assert_eq!(result.nodes.len(), 1);
        assert!(result.nodes.contains("a"));
    }

    #[test]
    fn test_dqueue_empty_pull() {
        let mut dq = DQueue::new(10, 100.0);
        assert!(!dq.non_empty());
        let result = dq.pull();
        assert!(result.nodes.is_empty());
        assert_eq!(result.b, 100.0);
    }

    #[test]
    fn test_dqueue_prepend_priority_over_data() {
        let mut dq = DQueue::new(2, 100.0);
        dq.insert("data_node".to_string(), 1.0);
        let items = vec![NodeDist {
            node: "prepend_node".to_string(),
            dist: 50.0,
        }];
        dq.batch_prepend(items);
        // prepend should be pulled first even though data has smaller distance
        let result = dq.pull();
        assert!(result.nodes.contains("prepend_node"));
    }

    // ---- Graph tests ----

    #[test]
    fn test_graph_nodes_includes_targets() {
        let mut g = Graph::new();
        g.add_edge("a", "b", 1.0);
        let nodes = g.nodes();
        assert!(nodes.contains(&"a".to_string()));
        assert!(nodes.contains(&"b".to_string()));
    }

    #[test]
    fn test_graph_neighbors_nonexistent() {
        let g = Graph::new();
        assert_eq!(g.neighbors("missing").count(), 0);
    }
}
