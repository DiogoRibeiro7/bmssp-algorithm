use bmssp::{run_sssp, DQueue, Graph, NodeDist};
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn gen_sparse(n: usize, edge_factor: usize, seed: u64) -> Graph {
    let mut g = Graph::new();
    // Ensure all nodes exist
    for i in 0..n {
        g.adj.insert(format!("n{}", i), Vec::new());
    }
    let mut state = seed;
    let m = edge_factor * n;
    for _ in 0..m {
        // simple LCG
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let u = (state >> 32) as usize % n;
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let v = (state >> 32) as usize % n;
        if u != v {
            let w = (((state >> 16) % 100) + 1) as f64;
            g.add_edge(&format!("n{}", u), &format!("n{}", v), w);
        }
    }
    g
}

fn gen_grid(width: usize, height: usize) -> Graph {
    let mut g = Graph::new();
    for y in 0..height {
        for x in 0..width {
            let u = format!("v{}_{}", x, y);
            if x + 1 < width {
                g.add_edge(&u, &format!("v{}_{}", x + 1, y), 1.0);
            }
            if y + 1 < height {
                g.add_edge(&u, &format!("v{}_{}", x, y + 1), 1.0);
            }
        }
    }
    g
}

fn bench_sssp(c: &mut Criterion) {
    let mut group = c.benchmark_group("run_sssp_sparse");
    for n in [100, 500, 1000, 5000].iter() {
        let g = gen_sparse(*n, 3, 42);
        group.bench_function(format!("n={}", n), |b| {
            b.iter(|| run_sssp(black_box(&g), "n0", false))
        });
    }
    group.finish();

    let mut group = c.benchmark_group("run_sssp_grid");
    for &(w, h) in &[(10usize, 10usize), (20, 20), (50, 50)] {
        let g = gen_grid(w, h);
        group.bench_function(format!("{}x{}", w, h), |b| {
            b.iter(|| run_sssp(black_box(&g), "v0_0", false))
        });
    }
    group.finish();
}

fn bench_dqueue(c: &mut Criterion) {
    c.bench_function("dqueue_insert", |b| {
        b.iter(|| {
            let mut dq = DQueue::new(100, 1e9);
            for i in 0..100 {
                dq.insert(format!("n{}", i), i as f64);
            }
            black_box(dq);
        })
    });

    c.bench_function("dqueue_pull_after_64_inserts", |b| {
        b.iter_with_setup(
            || {
                let mut dq = DQueue::new(16, 1e9);
                for i in 0..64 {
                    dq.insert(format!("n{}", i), i as f64);
                }
                dq
            },
            |mut dq| {
                let _ = dq.pull();
                black_box(dq);
            },
        )
    });

    c.bench_function("dqueue_batch_prepend", |b| {
        b.iter_with_setup(
            || {
                let items: Vec<NodeDist> = (0..32)
                    .map(|i| NodeDist {
                        node: format!("n{}", i),
                        dist: i as f64,
                    })
                    .collect();
                (DQueue::new(16, 1e9), items)
            },
            |(mut dq, items)| {
                dq.batch_prepend(items);
                black_box(dq);
            },
        )
    });
}

criterion_group!(benches, bench_sssp, bench_dqueue);
criterion_main!(benches);
