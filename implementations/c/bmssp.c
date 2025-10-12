#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <float.h>
#include <string.h>
#include <ctype.h>

#define INF DBL_MAX

// -------- Graph --------
typedef struct { int to; double w; } Edge;

typedef struct {
    Edge *edges;
    int count;
    int capacity;
} EdgeList;

typedef struct {
    int n;
    EdgeList *adj;
} Graph;

Graph* new_graph(int n) {
    Graph *g = (Graph*)malloc(sizeof(Graph));
    g->n = n;
    g->adj = (EdgeList*)calloc(n, sizeof(EdgeList));
    return g;
}

void add_edge(Graph *g, int u, int v, double w) {
    if (w < 0) {
        fprintf(stderr, "Only non-negative weights allowed\n");
        exit(1);
    }
    EdgeList *list = &g->adj[u];
    if (list->count == list->capacity) {
        list->capacity = list->capacity ? list->capacity * 2 : 4;
        list->edges = (Edge*)realloc(list->edges, list->capacity * sizeof(Edge));
    }
    list->edges[list->count++] = (Edge){v, w};
    // ensure adjacency for v exists
    if (!g->adj[v].edges && g->adj[v].count == 0) {
        g->adj[v].edges = NULL;
        g->adj[v].capacity = 0;
    }
}

void free_graph(Graph *g) {
    if (!g) return;
    for (int i = 0; i < g->n; i++) free(g->adj[i].edges);
    free(g->adj);
    free(g);
}

// -------- Name index and DOT parsing helpers --------

typedef struct {
    char **names;
    int count;
    int capacity;
} NameIndex;

void ni_init(NameIndex *ni) {
    ni->names = NULL;
    ni->count = 0;
    ni->capacity = 0;
}

void ni_free(NameIndex *ni) {
    for (int i = 0; i < ni->count; i++) free(ni->names[i]);
    free(ni->names);
    ni->names = NULL;
    ni->count = 0;
    ni->capacity = 0;
}

int ni_index_of(const NameIndex *ni, const char *name) {
    for (int i = 0; i < ni->count; i++) {
        if (strcmp(ni->names[i], name) == 0) return i;
    }
    return -1;
}

int ni_get_or_add(NameIndex *ni, const char *name) {
    int idx = ni_index_of(ni, name);
    if (idx >= 0) return idx;
    if (ni->count == ni->capacity) {
        ni->capacity = ni->capacity ? ni->capacity * 2 : 8;
        ni->names = (char**)realloc(ni->names, ni->capacity * sizeof(char*));
        if (!ni->names) {
            fprintf(stderr, "Memory allocation failed while growing name index\n");
            exit(1);
        }
    }
    ni->names[ni->count] = strdup(name);
    if (!ni->names[ni->count]) {
        fprintf(stderr, "Memory allocation failed while storing node name\n");
        exit(1);
    }
    return ni->count++;
}

typedef struct {
    int from;
    int to;
    double weight;
} EdgeRecord;

typedef struct {
    EdgeRecord *data;
    int count;
    int capacity;
} EdgeArray;

void ea_init(EdgeArray *ea) {
    ea->data = NULL;
    ea->count = 0;
    ea->capacity = 0;
}

void ea_free(EdgeArray *ea) {
    free(ea->data);
    ea->data = NULL;
    ea->count = 0;
    ea->capacity = 0;
}

void ea_push(EdgeArray *ea, int from, int to, double weight) {
    if (ea->count == ea->capacity) {
        ea->capacity = ea->capacity ? ea->capacity * 2 : 16;
        ea->data = (EdgeRecord*)realloc(ea->data, ea->capacity * sizeof(EdgeRecord));
        if (!ea->data) {
            fprintf(stderr, "Memory allocation failed while storing edges\n");
            exit(1);
        }
    }
    ea->data[ea->count++] = (EdgeRecord){from, to, weight};
}

void trim_whitespace(char *str) {
    char *start = str;
    while (*start && isspace((unsigned char)*start)) start++;
    if (start != str) memmove(str, start, strlen(start) + 1);
    size_t len = strlen(str);
    while (len > 0 && isspace((unsigned char)str[len - 1])) {
        str[len - 1] = '\0';
        len--;
    }
}

Graph* load_graph_from_dot(const char *filename, NameIndex *names) {
    ni_init(names);
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        fprintf(stderr, "Failed to open DOT file: %s\n", filename);
        return NULL;
    }

    EdgeArray edges; ea_init(&edges);
    char line[1024];

    while (fgets(line, sizeof(line), fp)) {
        char *arrow = strstr(line, "->");
        if (arrow) {
            char from_buf[256];
            char to_buf[256];
            size_t from_len = (size_t)(arrow - line);
            if (from_len >= sizeof(from_buf)) from_len = sizeof(from_buf) - 1;
            strncpy(from_buf, line, from_len);
            from_buf[from_len] = '\0';
            trim_whitespace(from_buf);
            char *rest = arrow + 2;
            while (*rest && isspace((unsigned char)*rest)) rest++;
            size_t to_len = 0;
            while (rest[to_len] && !isspace((unsigned char)rest[to_len]) && rest[to_len] != '[' && rest[to_len] != ';') {
                to_len++;
            }
            if (to_len >= sizeof(to_buf)) to_len = sizeof(to_buf) - 1;
            strncpy(to_buf, rest, to_len);
            to_buf[to_len] = '\0';
            trim_whitespace(to_buf);
            if (from_buf[0] == '\0' || to_buf[0] == '\0') continue;
            double weight = 1.0;
            char *label = strstr(rest + to_len, "label");
            if (label) {
                char *eq = strchr(label, '=');
                if (eq) {
                    weight = strtod(eq + 1, NULL);
                }
            }
            int from_idx = ni_get_or_add(names, from_buf);
            int to_idx = ni_get_or_add(names, to_buf);
            ea_push(&edges, from_idx, to_idx, weight);
        } else {
            char *semi = strchr(line, ';');
            if (semi) {
                char node_buf[256];
                size_t len = (size_t)(semi - line);
                if (len >= sizeof(node_buf)) len = sizeof(node_buf) - 1;
                strncpy(node_buf, line, len);
                node_buf[len] = '\0';
                trim_whitespace(node_buf);
                if (node_buf[0] && strcmp(node_buf, "}") != 0 && strncmp(node_buf, "digraph", 7) != 0) {
                    ni_get_or_add(names, node_buf);
                }
            }
        }
    }
    fclose(fp);

    if (names->count == 0) {
        fprintf(stderr, "DOT file %s did not contain any nodes\n", filename);
        ea_free(&edges);
        return NULL;
    }

    Graph *graph = new_graph(names->count);
    for (int i = 0; i < edges.count; i++) {
        EdgeRecord er = edges.data[i];
        add_edge(graph, er.from, er.to, er.weight);
    }
    ea_free(&edges);
    return graph;
}

// -------- IntArray helper (used as sets) --------
typedef struct {
    int *data;
    int count;
    int capacity;
} IntArray;

void ia_init(IntArray *a) {
    a->data = NULL;
    a->count = 0;
    a->capacity = 0;
}

void ia_free(IntArray *a) {
    free(a->data);
}

int ia_contains(const IntArray *a, int x) {
    for (int i = 0; i < a->count; i++) if (a->data[i] == x) return 1;
    return 0;
}

void ia_add_unique(IntArray *a, int x) {
    if (ia_contains(a, x)) return;
    if (a->count == a->capacity) {
        a->capacity = a->capacity ? a->capacity * 2 : 4;
        a->data = (int*)realloc(a->data, a->capacity * sizeof(int));
    }
    a->data[a->count++] = x;
}

void ia_copy(IntArray *dest, const IntArray *src) {
    dest->count = 0;
    dest->capacity = src->count;
    dest->data = (int*)realloc(dest->data, dest->capacity * sizeof(int));
    for (int i = 0; i < src->count; i++) dest->data[dest->count++] = src->data[i];
}

// -------- MinHeap --------
typedef struct { double dist; int node; } NodeDist;

typedef struct {
    NodeDist *data;
    int size;
    int capacity;
} MinHeap;

void heap_init(MinHeap *h) {
    h->data = NULL;
    h->size = 0;
    h->capacity = 0;
}

void heap_free(MinHeap *h) {
    free(h->data);
}

void heap_swap(NodeDist *a, NodeDist *b) {
    NodeDist tmp = *a; *a = *b; *b = tmp;
}

void heap_push(MinHeap *h, NodeDist nd) {
    if (h->size == h->capacity) {
        h->capacity = h->capacity ? h->capacity * 2 : 8;
        h->data = (NodeDist*)realloc(h->data, h->capacity * sizeof(NodeDist));
    }
    int i = h->size++;
    h->data[i] = nd;
    while (i > 0) {
        int parent = (i - 1) / 2;
        if (h->data[parent].dist <= h->data[i].dist) break;
        heap_swap(&h->data[parent], &h->data[i]);
        i = parent;
    }
}

NodeDist heap_pop(MinHeap *h) {
    NodeDist res = h->data[0];
    h->data[0] = h->data[--h->size];
    int i = 0;
    while (1) {
        int left = 2*i + 1, right = 2*i + 2, smallest = i;
        if (left < h->size && h->data[left].dist < h->data[smallest].dist) smallest = left;
        if (right < h->size && h->data[right].dist < h->data[smallest].dist) smallest = right;
        if (smallest == i) break;
        heap_swap(&h->data[i], &h->data[smallest]);
        i = smallest;
    }
    return res;
}

int heap_empty(MinHeap *h) { return h->size == 0; }

// -------- DQueue --------
typedef struct {
    int M;
    double B;
    MinHeap data;
    NodeDist *prepend;
    int pre_count;
    int pre_capacity;
} DQueue;

void dq_init(DQueue *dq, int M, double B) {
    dq->M = M; dq->B = B;
    heap_init(&dq->data);
    dq->prepend = NULL; dq->pre_count = 0; dq->pre_capacity = 0;
}

void dq_free(DQueue *dq) {
    heap_free(&dq->data);
    free(dq->prepend);
}

void dq_insert(DQueue *dq, int node, double dist) {
    if (dist >= dq->B) return;
    heap_push(&dq->data, (NodeDist){dist, node});
}

void dq_batch_prepend(DQueue *dq, NodeDist *items, int count) {
    for (int i = 0; i < count; i++) {
        if (items[i].dist < dq->B) {
            if (dq->pre_count == dq->pre_capacity) {
                dq->pre_capacity = dq->pre_capacity ? dq->pre_capacity * 2 : 8;
                dq->prepend = (NodeDist*)realloc(dq->prepend, dq->pre_capacity * sizeof(NodeDist));
            }
            dq->prepend[dq->pre_count++] = items[i];
        }
    }
}

int dq_non_empty(DQueue *dq) {
    return dq->pre_count > 0 || !heap_empty(&dq->data);
}

void dq_pull(DQueue *dq, double *Bi, IntArray *Si) {
    ia_init(Si);
    if (dq->pre_count > 0) {
        int take = dq->pre_count < dq->M ? dq->pre_count : dq->M;
        *Bi = dq->prepend[0].dist;
        for (int i = 0; i < take; i++) ia_add_unique(Si, dq->prepend[i].node);
        dq->pre_count -= take;
        for (int i = 0; i < dq->pre_count; i++) dq->prepend[i] = dq->prepend[i+take];
        return;
    }
    if (heap_empty(&dq->data)) { *Bi = dq->B; return; }
    NodeDist *tmp = (NodeDist*)malloc(dq->M * sizeof(NodeDist));
    int cnt = 0;
    while (!heap_empty(&dq->data) && cnt < dq->M) tmp[cnt++] = heap_pop(&dq->data);
    *Bi = cnt ? tmp[0].dist : dq->B;
    for (int i = 0; i < cnt; i++) ia_add_unique(Si, tmp[i].node);
    free(tmp);
}

// -------- Result containers for API consistency --------
typedef struct {
    IntArray P;
    IntArray W;
} PivotResult;

typedef struct {
    double B;
    IntArray U;
} BaseCaseResult;

typedef struct {
    double B;
    IntArray U;
} BMSSPResult;

// -------- Algorithm 1: FindPivots --------
int subtree_size_rec(int u, IntArray *children, int *seen) {
    if (seen[u]) return 0;
    seen[u] = 1;
    int size = 1;
    for (int i = 0; i < children[u].count; i++) {
        size += subtree_size_rec(children[u].data[i], children, seen);
    }
    seen[u] = 0;
    return size;
}

PivotResult find_pivots(Graph *graph, double B, IntArray *S, double *d_hat, int *pred, IntArray *complete, int k, int verbose) {
    IntArray W; ia_init(&W); ia_copy(&W, S);
    IntArray W_prev; ia_init(&W_prev); ia_copy(&W_prev, S);
    if (verbose) printf("find_pivots: start |S|=%d, B=%g\n", S->count, B);
    for (int iter = 1; iter <= k; iter++) {
        IntArray W_i; ia_init(&W_i);
        for (int idx = 0; idx < W_prev.count; idx++) {
            int u = W_prev.data[idx];
            double du = d_hat[u];
            if (du >= B) continue;
            EdgeList *lst = &graph->adj[u];
            for (int e = 0; e < lst->count; e++) {
                int v = lst->edges[e].to; double w = lst->edges[e].w;
                if (du + w <= d_hat[v]) {
                    d_hat[v] = du + w;
                    pred[v] = u;
                    if (du + w < B) ia_add_unique(&W_i, v);
                }
            }
        }
        for (int i = 0; i < W_i.count; i++) ia_add_unique(&W, W_i.data[i]);
        if (W.count > k * S->count) {
            if (verbose) printf("find_pivots: early termination |W| > k*|S|\n");
            PivotResult res = {0};
            ia_init(&res.P); ia_copy(&res.P, S);
            res.W = W;
            ia_free(&W_i); ia_free(&W_prev);
            return res;
        }
        ia_free(&W_prev);
        ia_init(&W_prev); ia_copy(&W_prev, &W_i);
        ia_free(&W_i);
    }
    IntArray *children = (IntArray*)malloc(graph->n * sizeof(IntArray));
    int *indeg = (int*)calloc(graph->n, sizeof(int));
    if (!children || !indeg) {
        fprintf(stderr, "find_pivots: memory allocation failed\n");
        free(children); free(indeg); ia_free(&W_prev); ia_free(&W); exit(1);
    }
    for (int i = 0; i < graph->n; i++) ia_init(&children[i]);
    for (int idx = 0; idx < W.count; idx++) {
        int u = W.data[idx]; double du = d_hat[u];
        EdgeList *lst = &graph->adj[u];
        for (int e = 0; e < lst->count; e++) {
            int v = lst->edges[e].to; double w = lst->edges[e].w;
            if (ia_contains(&W, v) && fabs(d_hat[v] - (du + w)) < 1e-12) {
                ia_add_unique(&children[u], v);
                indeg[v]++;
            }
        }
    }

    PivotResult res; ia_init(&res.P); res.W = W;
    int *seen = (int*)calloc(graph->n, sizeof(int));
    if (!seen) {
        fprintf(stderr, "find_pivots: memory allocation failed\n");
        for (int i = 0; i < graph->n; i++) ia_free(&children[i]);
        free(children); free(indeg); ia_free(&W_prev); ia_free(&res.P); ia_free(&W); exit(1);
    }
    for (int idx = 0; idx < S->count; idx++) {
        int u = S->data[idx];
        if (indeg[u] == 0 && subtree_size_rec(u, children, seen) >= k) ia_add_unique(&res.P, u);
    }
    if (verbose) {
        printf("find_pivots: pivots={");
        for (int i = 0; i < res.P.count; i++) {
            if (i) printf(", ");
            printf("%d", res.P.data[i]);
        }
        printf("}\n");
    }
    free(seen);
    for (int i = 0; i < graph->n; i++) ia_free(&children[i]);
    free(children); free(indeg); ia_free(&W_prev);
    return res;
}

// -------- Algorithm 2: BaseCase --------
BaseCaseResult base_case(Graph *graph, double B, IntArray *S, double *d_hat, int *pred, IntArray *complete, int k, int verbose) {
    int x = S->data[0];
    IntArray U0; ia_init(&U0); ia_add_unique(&U0, x);
    MinHeap H; heap_init(&H); heap_push(&H, (NodeDist){d_hat[x], x});
    int *visited = (int*)calloc(graph->n, sizeof(int));
    if (verbose) printf("base_case: start from %d with B=%g\n", x, B);
    while (!heap_empty(&H) && U0.count < k + 1) {
        NodeDist nd = heap_pop(&H); int u = nd.node; double du = nd.dist;
        if (visited[u]) continue; visited[u] = 1; ia_add_unique(&U0, u); ia_add_unique(complete, u);
        EdgeList *lst = &graph->adj[u];
        for (int e = 0; e < lst->count; e++) {
            int v = lst->edges[e].to; double w = lst->edges[e].w;
            if (du + w <= d_hat[v] && du + w < B) {
                d_hat[v] = du + w; pred[v] = u; heap_push(&H, (NodeDist){d_hat[v], v});
            }
        }
    }
    BaseCaseResult res;
    if (U0.count <= k) {
        if (verbose) printf("base_case: early termination |U0| <= k\n");
        res.B = B;
        res.U = U0;
    } else {
        double Bp = -INFINITY;
        for (int i = 0; i < U0.count; i++) if (d_hat[U0.data[i]] > Bp) Bp = d_hat[U0.data[i]];
        res.B = Bp;
        ia_init(&res.U);
        for (int i = 0; i < U0.count; i++) if (d_hat[U0.data[i]] < Bp) ia_add_unique(&res.U, U0.data[i]);
        ia_free(&U0);
        if (verbose) printf("base_case: computed B'=%g\n", res.B);
    }
    free(visited); heap_free(&H);
    return res;
}

// -------- Algorithm 3: BMSSP --------
BMSSPResult bmssp(Graph *graph, int l, double B, IntArray *S, double *d_hat, int *pred, IntArray *complete, int k, int t, int verbose) {
    if (verbose) printf("bmssp: level=%d, B=%g, |S|=%d\n", l, B, S->count);
    if (l == 0) {
        BaseCaseResult bc = base_case(graph, B, S, d_hat, pred, complete, k, verbose);
        if (verbose) printf("bmssp: base case returns B=%g, |U|=%d\n", bc.B, bc.U.count);
        BMSSPResult res = {bc.B, bc.U};
        return res;
    }
    PivotResult piv = find_pivots(graph, B, S, d_hat, pred, complete, k, verbose);
    IntArray P = piv.P; IntArray W = piv.W;
    if (verbose) {
        printf("bmssp: pivots={");
        for (int i = 0; i < P.count; i++) {
            if (i) printf(", ");
            printf("%d", P.data[i]);
        }
        printf("}\n");
    }
    int M = 1 << ((l - 1) * t);
    DQueue D; dq_init(&D, M, B);
    for (int i = 0; i < P.count; i++) dq_insert(&D, P.data[i], d_hat[P.data[i]]);
    IntArray U; ia_init(&U);
    double B0_prime = B;
    for (int i = 0; i < P.count; i++) if (d_hat[P.data[i]] < B0_prime) B0_prime = d_hat[P.data[i]];
    if (verbose) printf("bmssp: B0'=%g\n", B0_prime);
    while (U.count < k * (1 << (l * t)) && dq_non_empty(&D)) {
        double Bi; IntArray Si; dq_pull(&D, &Bi, &Si);
        BMSSPResult rec = bmssp(graph, l - 1, Bi, &Si, d_hat, pred, complete, k, t, verbose);
        double B_prime_i = rec.B; IntArray U_i = rec.U;
        for (int j = 0; j < U_i.count; j++) ia_add_unique(&U, U_i.data[j]);
        IntArray K; ia_init(&K);
        for (int j = 0; j < U_i.count; j++) {
            int u = U_i.data[j]; EdgeList *lst = &graph->adj[u];
            for (int e = 0; e < lst->count; e++) {
                int v = lst->edges[e].to; double w = lst->edges[e].w;
                if (d_hat[u] + w <= d_hat[v]) {
                    d_hat[v] = d_hat[u] + w;
                    pred[v] = u;
                    if (Bi <= d_hat[v] && d_hat[v] < B) dq_insert(&D, v, d_hat[v]);
                    else if (B_prime_i <= d_hat[v] && d_hat[v] < Bi) ia_add_unique(&K, v);
                }
            }
        }
        NodeDist *prepend = NULL; int pc = 0;
        if (K.count + Si.count) {
            prepend = (NodeDist*)malloc((K.count + Si.count) * sizeof(NodeDist));
            for (int j = 0; j < K.count; j++) prepend[pc++] = (NodeDist){d_hat[K.data[j]], K.data[j]};
            for (int j = 0; j < Si.count; j++) {
                int x = Si.data[j]; double dist = d_hat[x];
                if (B_prime_i <= dist && dist < Bi) prepend[pc++] = (NodeDist){dist, x};
            }
            dq_batch_prepend(&D, prepend, pc);
            free(prepend);
        }
        ia_free(&K); ia_free(&Si); ia_free(&U_i);
    }
    if (verbose) {
        const char *reason = "condition";
        if (U.count >= k * (1 << (l * t))) reason = "U size reached";
        else if (!dq_non_empty(&D)) reason = "queue empty";
        printf("bmssp: terminating loop due to %s\n", reason);
    }
    double B_prime = B0_prime < B ? B0_prime : B;
    for (int i = 0; i < W.count; i++) {
        int x = W.data[i]; if (d_hat[x] < B_prime) ia_add_unique(&U, x);
    }
    for (int i = 0; i < U.count; i++) ia_add_unique(complete, U.data[i]);
    if (verbose) printf("bmssp: returning B=%g, |U|=%d\n", B_prime, U.count);
    BMSSPResult res = {B_prime, U};
    dq_free(&D); ia_free(&P); ia_free(&W);
    return res;
}

// -------- Main Driver --------
void run_sssp(Graph *graph, int source, double *d_hat, int *pred, int verbose) {
    int n = graph->n;
    double log2n = log2((double)n);
    int k = (int)fmax(1.0, pow(log2n, 1.0/3.0));
    int t = (int)fmax(1.0, pow(log2n, 2.0/3.0));
    int l = (int)ceil(log2n / t);
    for (int i = 0; i < n; i++) { d_hat[i] = INF; pred[i] = -1; }
    d_hat[source] = 0.0; pred[source] = source;
    IntArray complete; ia_init(&complete); ia_add_unique(&complete, source);
    IntArray S; ia_init(&S); ia_add_unique(&S, source);
    BMSSPResult res = bmssp(graph, l, INF, &S, d_hat, pred, &complete, k, t, verbose);
    ia_free(&res.U);
    ia_free(&complete); ia_free(&S);
}

void dijkstra_shortest_paths(Graph *graph, int source, double *dist, int *pred) {
    int n = graph->n;
    for (int i = 0; i < n; i++) { dist[i] = INF; pred[i] = -1; }
    dist[source] = 0.0; pred[source] = source;
    MinHeap heap; heap_init(&heap);
    heap_push(&heap, (NodeDist){0.0, source});
    int *visited = (int*)calloc(n, sizeof(int));
    if (!visited) {
        fprintf(stderr, "Memory allocation failed in Dijkstra\n");
        heap_free(&heap);
        return;
    }
    while (!heap_empty(&heap)) {
        NodeDist nd = heap_pop(&heap);
        int u = nd.node;
        if (visited[u]) continue;
        visited[u] = 1;
        EdgeList *lst = &graph->adj[u];
        for (int e = 0; e < lst->count; e++) {
            int v = lst->edges[e].to; double w = lst->edges[e].w;
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                pred[v] = u;
                heap_push(&heap, (NodeDist){dist[v], v});
            }
        }
    }
    free(visited);
    heap_free(&heap);
}

void print_path_from_source(int source, int target, const NameIndex *names, const double *dist, const int *pred) {
    const char *src_name = names->names[source];
    const char *dst_name = names->names[target];
    if (dist[target] == INF || pred[target] == -1) {
        if (target == source && dist[target] == 0.0) {
            printf("Shortest path from %s to %s (distance 0): %s\n", src_name, dst_name, src_name);
            return;
        }
        printf("No path from %s to %s.\n", src_name, dst_name);
        return;
    }
    int n = names->count;
    int *path = (int*)malloc(n * sizeof(int));
    if (!path) {
        fprintf(stderr, "Memory allocation failed while printing path\n");
        return;
    }
    int len = 0;
    int current = target;
    while (current != -1 && len < n) {
        path[len++] = current;
        if (current == source) break;
        current = pred[current];
    }
    if (current == -1 || (len == n && path[len - 1] != source)) {
        printf("No path from %s to %s.\n", src_name, dst_name);
        free(path);
        return;
    }
    printf("Shortest path from %s to %s (distance %.6g): ", src_name, dst_name, dist[target]);
    for (int i = len - 1; i >= 0; i--) {
        printf("%s", names->names[path[i]]);
        if (i) printf(" -> ");
    }
    printf("\n");
    free(path);
}

void print_all_paths(int source, const NameIndex *names, const double *dist, const int *pred) {
    for (int i = 0; i < names->count; i++) {
        print_path_from_source(source, i, names, dist, pred);
    }
}

int main(int argc, char **argv) {
    if (argc < 3 || argc > 4) {
        fprintf(stderr, "Usage: %s <graph.dot> <source> [target]\n", argv[0]);
        return 1;
    }

    const char *dot_file = argv[1];
    const char *source_name = argv[2];
    const char *target_name = (argc == 4) ? argv[3] : NULL;

    NameIndex names;
    Graph *graph = load_graph_from_dot(dot_file, &names);
    if (!graph) {
        ni_free(&names);
        return 1;
    }

    int source_idx = ni_index_of(&names, source_name);
    if (source_idx < 0) {
        fprintf(stderr, "Source node '%s' not found in %s\n", source_name, dot_file);
        free_graph(graph);
        ni_free(&names);
        return 1;
    }

    int target_idx = -1;
    if (target_name) {
        target_idx = ni_index_of(&names, target_name);
        if (target_idx < 0) {
            fprintf(stderr, "Target node '%s' not found in %s\n", target_name, dot_file);
            free_graph(graph);
            ni_free(&names);
            return 1;
        }
    }

    double *dist = (double*)malloc(graph->n * sizeof(double));
    int *pred = (int*)malloc(graph->n * sizeof(int));
    if (!dist || !pred) {
        fprintf(stderr, "Memory allocation failed for algorithm buffers\n");
        free(dist); free(pred);
        free_graph(graph);
        ni_free(&names);
        return 1;
    }

    dijkstra_shortest_paths(graph, source_idx, dist, pred);

    if (target_name) {
        print_path_from_source(source_idx, target_idx, &names, dist, pred);
    } else {
        print_all_paths(source_idx, &names, dist, pred);
    }

    free(dist);
    free(pred);
    free_graph(graph);
    ni_free(&names);
    return 0;
}

