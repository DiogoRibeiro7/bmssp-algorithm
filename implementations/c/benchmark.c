/*
 * benchmark.c - timing-based benchmark for the C BMSSP implementation.
 *
 * Generates sparse random, scale-free, and grid graphs of varying sizes,
 * then times both run_sssp (BMSSP) and dijkstra_shortest_paths on each.
 *
 * Output: CSV to stdout
 *   graph_type,n,m,algo,time_ms
 *
 * Build:
 *   gcc -Wall -Wextra -std=c11 -O2 benchmark.c -lm -o benchmark
 *
 * Run:
 *   ./benchmark > results.csv
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Pull in the algorithm by including the translation unit. */
#include "bmssp.c"

static double time_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1e6;
}

/* Generate a sparse random graph with approximately m=edge_factor*n edges. */
static Graph *gen_sparse(int n, int edge_factor) {
    Graph *g = (Graph *)malloc(sizeof(Graph));
    g->n = n;
    g->adj = (EdgeList *)calloc(n, sizeof(EdgeList));
    int m = edge_factor * n;
    for (int i = 0; i < m; i++) {
        int u = rand() % n;
        int v = rand() % n;
        if (u == v) continue;
        double w = (double)(rand() % 100) + 1.0;
        add_edge(g, u, v, w);
    }
    return g;
}

/* Generate a grid graph (width x height) with unit weights. */
static Graph *gen_grid(int width, int height) {
    int n = width * height;
    Graph *g = (Graph *)malloc(sizeof(Graph));
    g->n = n;
    g->adj = (EdgeList *)calloc(n, sizeof(EdgeList));
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            int u = y * width + x;
            if (x + 1 < width) add_edge(g, u, u + 1, 1.0);
            if (y + 1 < height) add_edge(g, u, u + width, 1.0);
        }
    }
    return g;
}

/* Scale-free via preferential attachment: each new node connects to k existing ones
 * with probability proportional to their current in-degree. */
static Graph *gen_scale_free(int n, int k_attach) {
    Graph *g = (Graph *)malloc(sizeof(Graph));
    g->n = n;
    g->adj = (EdgeList *)calloc(n, sizeof(EdgeList));
    int *deg = (int *)calloc(n, sizeof(int));
    int total_deg = 0;
    for (int i = 0; i < k_attach && i < n; i++) {
        if (i > 0) {
            add_edge(g, i, 0, 1.0 + (rand() % 10));
            deg[0]++;
            total_deg++;
        }
    }
    for (int i = k_attach; i < n; i++) {
        for (int j = 0; j < k_attach; j++) {
            int target = 0;
            if (total_deg > 0) {
                int r = rand() % total_deg;
                int acc = 0;
                for (int t = 0; t < i; t++) {
                    acc += deg[t];
                    if (acc > r) {
                        target = t;
                        break;
                    }
                }
            }
            if (target != i) {
                add_edge(g, i, target, 1.0 + (rand() % 10));
                deg[target]++;
                total_deg++;
            }
        }
    }
    free(deg);
    return g;
}

static int count_edges(Graph *g) {
    int m = 0;
    for (int i = 0; i < g->n; i++) m += g->adj[i].count;
    return m;
}

static void bench(const char *type, Graph *g) {
    int n = g->n;
    int m = count_edges(g);
    double *dist = (double *)malloc(n * sizeof(double));
    int *pred = (int *)malloc(n * sizeof(int));

    double t0 = time_ms();
    run_sssp(g, 0, dist, pred, 0);
    double t_bmssp = time_ms() - t0;

    t0 = time_ms();
    dijkstra_shortest_paths(g, 0, dist, pred);
    double t_dijkstra = time_ms() - t0;

    printf("%s,%d,%d,bmssp,%.3f\n", type, n, m, t_bmssp);
    printf("%s,%d,%d,dijkstra,%.3f\n", type, n, m, t_dijkstra);

    free(dist);
    free(pred);
    free_graph(g);
}

int main(void) {
    srand(42);
    printf("graph_type,n,m,algo,time_ms\n");

    int sizes[] = {100, 500, 1000, 5000, 10000};
    int n_sizes = sizeof(sizes) / sizeof(sizes[0]);

    for (int i = 0; i < n_sizes; i++) {
        bench("sparse", gen_sparse(sizes[i], 3));
        bench("scale_free", gen_scale_free(sizes[i], 3));
    }

    bench("grid", gen_grid(10, 10));
    bench("grid", gen_grid(20, 20));
    bench("grid", gen_grid(50, 50));
    bench("grid", gen_grid(100, 100));

    return 0;
}
