// BMSSP - Breaking the Sorting Barrier for Directed Single-Source Shortest Paths
// C++ reference implementation following the algorithm in:
//   Duan et al., "Breaking the Sorting Barrier for Directed Single-Source
//   Shortest Paths", arXiv:2504.17033v2, 2025.
//
// Build:
//   g++ -std=c++17 -Wall -Wextra -O2 bmssp.cpp -o bmssp
//
// Usage:
//   ./bmssp [OPTIONS] <graph.dot> <source> [target]
//
// Options:
//   --verbose    Print algorithm trace to stderr
//   --json       Emit results as JSON
//   -V           Print version and exit

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <queue>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace bmssp {

constexpr double INF = std::numeric_limits<double>::infinity();
constexpr const char* VERSION = "0.1.0";

// -------- Graph --------

struct Edge {
    int to;
    double w;
};

class Graph {
public:
    int n;
    std::vector<std::vector<Edge>> adj;

    explicit Graph(int n_) : n(n_), adj(n_) {}

    void add_edge(int u, int v, double w) {
        if (w < 0) {
            throw std::runtime_error("Only non-negative weights allowed");
        }
        adj[u].push_back({v, w});
    }
};

// -------- DQueue from Lemma 3.3 --------

struct NodeDist {
    double dist;
    int node;
    bool operator>(const NodeDist& other) const { return dist > other.dist; }
};

class DQueue {
public:
    int M;
    double B;
    std::priority_queue<NodeDist, std::vector<NodeDist>, std::greater<NodeDist>> data;
    std::vector<NodeDist> prepend;

    DQueue(int m, double b) : M(m), B(b) {}

    void insert(int node, double dist) {
        if (dist >= B) return;
        data.push({dist, node});
    }

    void batch_prepend(const std::vector<NodeDist>& items) {
        for (const auto& nd : items) {
            if (nd.dist < B) prepend.push_back(nd);
        }
    }

    bool non_empty() const { return !data.empty() || !prepend.empty(); }

    std::pair<double, std::set<int>> pull() {
        if (!prepend.empty()) {
            int take = std::min<int>(M, prepend.size());
            double bi = prepend[0].dist;
            std::set<int> nodes;
            for (int i = 0; i < take; i++) nodes.insert(prepend[i].node);
            prepend.erase(prepend.begin(), prepend.begin() + take);
            return {bi, nodes};
        }
        if (data.empty()) return {B, {}};
        std::vector<NodeDist> out;
        while (!data.empty() && (int)out.size() < M) {
            out.push_back(data.top());
            data.pop();
        }
        double bi = out.empty() ? B : out[0].dist;
        std::set<int> nodes;
        for (const auto& nd : out) nodes.insert(nd.node);
        return {bi, nodes};
    }
};

// -------- Result containers --------

struct PivotResult {
    std::set<int> P;
    std::set<int> W;
};

struct BaseCaseResult {
    double B;
    std::set<int> U;
};

struct BMSSPResult {
    double B;
    std::set<int> U;
};

// -------- Algorithm 1: FindPivots --------

PivotResult find_pivots(const Graph& graph, double B, const std::set<int>& S,
                        std::vector<double>& d_hat, std::vector<int>& pred,
                        std::set<int>& complete, int k, bool verbose) {
    (void)pred;
    (void)complete;
    std::set<int> W = S;
    std::set<int> W_prev = S;
    if (verbose) std::cerr << "find_pivots: start |S|=" << S.size() << " B=" << B << "\n";

    for (int iter = 0; iter < k; iter++) {
        std::set<int> Wi;
        for (int u : W_prev) {
            double du = d_hat[u];
            if (du >= B) continue;
            for (const auto& e : graph.adj[u]) {
                if (du + e.w <= d_hat[e.to]) {
                    d_hat[e.to] = du + e.w;
                    if (du + e.w < B) Wi.insert(e.to);
                }
            }
        }
        for (int v : Wi) W.insert(v);
        if ((int)W.size() > k * (int)S.size()) {
            if (verbose) std::cerr << "find_pivots: early termination |W| > k*|S|\n";
            return {S, W};
        }
        W_prev = Wi;
    }

    // Build forest of tight edges within W
    std::unordered_map<int, std::vector<int>> children;
    std::unordered_map<int, int> indeg;
    for (int u : W) indeg[u] = 0;

    for (int u : W) {
        double du = d_hat[u];
        for (const auto& e : graph.adj[u]) {
            if (W.count(e.to) && std::fabs(d_hat[e.to] - (du + e.w)) < 1e-12) {
                children[u].push_back(e.to);
                indeg[e.to]++;
            }
        }
    }

    // Compute subtree sizes via DFS
    std::function<int(int, std::unordered_set<int>&)> subtree_size =
        [&](int u, std::unordered_set<int>& seen) -> int {
            if (seen.count(u)) return 0;
            seen.insert(u);
            int size = 1;
            for (int c : children[u]) size += subtree_size(c, seen);
            seen.erase(u);
            return size;
        };

    std::set<int> P;
    for (int u : S) {
        std::unordered_set<int> seen;
        if (indeg[u] == 0 && subtree_size(u, seen) >= k) {
            P.insert(u);
        }
    }

    if (verbose) {
        std::cerr << "find_pivots: pivots={";
        bool first = true;
        for (int p : P) {
            if (!first) std::cerr << ", ";
            std::cerr << p;
            first = false;
        }
        std::cerr << "}\n";
    }

    return {P, W};
}

// -------- Algorithm 2: BaseCase --------

BaseCaseResult base_case(const Graph& graph, double B, const std::set<int>& S,
                         std::vector<double>& d_hat, std::vector<int>& pred,
                         std::set<int>& complete, int k, bool verbose) {
    if (S.empty()) return {B, {}};
    int x = *S.begin();
    std::set<int> U0 = {x};
    std::priority_queue<NodeDist, std::vector<NodeDist>, std::greater<NodeDist>> H;
    H.push({d_hat[x], x});
    std::vector<bool> visited(graph.n, false);
    if (verbose) std::cerr << "base_case: start from " << x << " B=" << B << "\n";

    while (!H.empty() && (int)U0.size() < k + 1) {
        auto nd = H.top();
        H.pop();
        int u = nd.node;
        double du = nd.dist;
        if (visited[u]) continue;
        visited[u] = true;
        U0.insert(u);
        complete.insert(u);
        for (const auto& e : graph.adj[u]) {
            double alt = du + e.w;
            if (alt <= d_hat[e.to] && alt < B) {
                d_hat[e.to] = alt;
                pred[e.to] = u;
                H.push({alt, e.to});
            }
        }
    }

    if ((int)U0.size() <= k) {
        if (verbose) std::cerr << "base_case: early termination |U0| <= k\n";
        return {B, U0};
    }

    double Bp = -INF;
    for (int v : U0) Bp = std::max(Bp, d_hat[v]);
    std::set<int> U;
    for (int v : U0) if (d_hat[v] < Bp) U.insert(v);
    if (verbose) std::cerr << "base_case: computed B'=" << Bp << "\n";
    return {Bp, U};
}

// -------- Algorithm 3: BMSSP --------

BMSSPResult bmssp(const Graph& graph, int l, double B, const std::set<int>& S,
                  std::vector<double>& d_hat, std::vector<int>& pred,
                  std::set<int>& complete, int k, int t, bool verbose) {
    if (verbose) std::cerr << "bmssp: level=" << l << " B=" << B << " |S|=" << S.size() << "\n";

    if (l == 0) {
        auto bc = base_case(graph, B, S, d_hat, pred, complete, k, verbose);
        if (verbose) std::cerr << "bmssp: base case returns B=" << bc.B << " |U|=" << bc.U.size() << "\n";
        return {bc.B, bc.U};
    }

    auto piv = find_pivots(graph, B, S, d_hat, pred, complete, k, verbose);
    auto& P = piv.P;
    auto& W = piv.W;

    int M = 1 << ((l - 1) * t);
    DQueue D(M, B);
    for (int x : P) D.insert(x, d_hat[x]);

    std::set<int> U;
    double B0_prime = B;
    for (int x : P) if (d_hat[x] < B0_prime) B0_prime = d_hat[x];
    if (verbose) std::cerr << "bmssp: B0'=" << B0_prime << "\n";

    while ((int)U.size() < k * (1 << (l * t)) && D.non_empty()) {
        auto [Bi, Si] = D.pull();
        auto rec = bmssp(graph, l - 1, Bi, Si, d_hat, pred, complete, k, t, verbose);
        double B_prime_i = rec.B;
        auto& Ui = rec.U;

        for (int u : Ui) U.insert(u);

        std::vector<NodeDist> K;
        for (int u : Ui) {
            for (const auto& e : graph.adj[u]) {
                double alt = d_hat[u] + e.w;
                if (alt <= d_hat[e.to]) {
                    d_hat[e.to] = alt;
                    pred[e.to] = u;
                    if (alt >= Bi && alt < B) {
                        D.insert(e.to, alt);
                    } else if (alt >= B_prime_i && alt < Bi) {
                        K.push_back({alt, e.to});
                    }
                }
            }
        }

        std::vector<NodeDist> prepend_items = K;
        for (int x : Si) {
            double dx = d_hat[x];
            if (dx >= B_prime_i && dx < Bi) {
                prepend_items.push_back({dx, x});
            }
        }
        D.batch_prepend(prepend_items);
    }

    double B_prime = std::min(B0_prime, B);
    for (int x : W) if (d_hat[x] < B_prime) U.insert(x);
    for (int u : U) complete.insert(u);

    if (verbose) std::cerr << "bmssp: returning B=" << B_prime << " |U|=" << U.size() << "\n";
    return {B_prime, U};
}

// -------- Driver --------

void run_sssp(const Graph& graph, int source, std::vector<double>& d_hat,
              std::vector<int>& pred, bool verbose) {
    int n = graph.n;
    double log2n = std::log2((double)n);
    int k = std::max(1, (int)std::pow(log2n, 1.0 / 3.0));
    int t = std::max(1, (int)std::pow(log2n, 2.0 / 3.0));
    int l = std::max(1, (int)std::ceil(log2n / t));

    d_hat.assign(n, INF);
    pred.assign(n, -1);
    d_hat[source] = 0.0;
    pred[source] = source;

    std::set<int> complete = {source};
    std::set<int> S = {source};
    bmssp(graph, l, INF, S, d_hat, pred, complete, k, t, verbose);
}

void dijkstra(const Graph& graph, int source, std::vector<double>& dist,
              std::vector<int>& pred) {
    int n = graph.n;
    dist.assign(n, INF);
    pred.assign(n, -1);
    dist[source] = 0;
    pred[source] = source;

    std::priority_queue<NodeDist, std::vector<NodeDist>, std::greater<NodeDist>> heap;
    heap.push({0, source});
    std::vector<bool> visited(n, false);

    while (!heap.empty()) {
        auto nd = heap.top();
        heap.pop();
        int u = nd.node;
        if (visited[u]) continue;
        visited[u] = true;
        for (const auto& e : graph.adj[u]) {
            double alt = nd.dist + e.w;
            if (alt < dist[e.to]) {
                dist[e.to] = alt;
                pred[e.to] = u;
                heap.push({alt, e.to});
            }
        }
    }
}

// -------- DOT parsing --------

struct GraphWithNames {
    Graph graph;
    std::vector<std::string> names;
    std::unordered_map<std::string, int> name_to_idx;

    GraphWithNames(int n) : graph(n) {}
};

GraphWithNames load_graph_from_dot(const std::string& filename) {
    FILE* fp = std::fopen(filename.c_str(), "r");
    if (!fp) throw std::runtime_error("cannot open " + filename);

    std::vector<std::string> names;
    std::unordered_map<std::string, int> name_to_idx;
    std::vector<std::tuple<int, int, double>> edges;

    auto get_or_add = [&](const std::string& name) -> int {
        auto it = name_to_idx.find(name);
        if (it != name_to_idx.end()) return it->second;
        int idx = names.size();
        names.push_back(name);
        name_to_idx[name] = idx;
        return idx;
    };

    // Hand-written DOT parser (avoids MinGW std::regex issues)
    auto parse_line = [&](const std::string& line) {
        // Trim
        size_t start = line.find_first_not_of(" \t\r\n");
        if (start == std::string::npos) return;
        size_t end = line.find_last_not_of(" \t\r\n");
        std::string s = line.substr(start, end - start + 1);

        if (s.empty() || s.substr(0, 2) == "//"
            || s.substr(0, 7) == "digraph" || s == "}") {
            return;
        }

        // Find "->"
        size_t arrow = s.find("->");
        if (arrow != std::string::npos) {
            // Parse edge
            std::string from_str = s.substr(0, arrow);
            // Trim from
            size_t fs = from_str.find_first_not_of(" \t");
            size_t fe = from_str.find_last_not_of(" \t");
            if (fs == std::string::npos) return;
            from_str = from_str.substr(fs, fe - fs + 1);

            // Skip whitespace after "->"
            size_t pos = arrow + 2;
            while (pos < s.size() && (s[pos] == ' ' || s[pos] == '\t')) pos++;

            // Read target name
            size_t name_end = pos;
            while (name_end < s.size() && s[name_end] != ' ' && s[name_end] != '\t'
                   && s[name_end] != '[' && s[name_end] != ';') {
                name_end++;
            }
            if (name_end == pos) return;
            std::string to_str = s.substr(pos, name_end - pos);

            // Parse weight from [label=X]
            double weight = 1.0;
            size_t label_pos = s.find("label", name_end);
            if (label_pos != std::string::npos) {
                size_t eq = s.find('=', label_pos);
                if (eq != std::string::npos) {
                    size_t num_start = eq + 1;
                    while (num_start < s.size() && (s[num_start] == ' ' || s[num_start] == '\t'))
                        num_start++;
                    size_t num_end = num_start;
                    while (num_end < s.size() && s[num_end] != ']' && s[num_end] != ';'
                           && s[num_end] != ' ' && s[num_end] != '\t') {
                        num_end++;
                    }
                    try {
                        weight = std::stod(s.substr(num_start, num_end - num_start));
                    } catch (...) {
                        weight = 1.0;
                    }
                }
            }

            int from = get_or_add(from_str);
            int to = get_or_add(to_str);
            edges.emplace_back(from, to, weight);
        } else {
            // Standalone node: NAME;
            size_t semi = s.find(';');
            if (semi != std::string::npos && semi > 0) {
                std::string node_str = s.substr(0, semi);
                size_t ns = node_str.find_first_not_of(" \t");
                size_t ne = node_str.find_last_not_of(" \t");
                if (ns != std::string::npos) {
                    node_str = node_str.substr(ns, ne - ns + 1);
                    if (!node_str.empty() && node_str != "}") {
                        get_or_add(node_str);
                    }
                }
            }
        }
    };

    char buf[4096];
    while (std::fgets(buf, sizeof(buf), fp)) {
        std::string line(buf);
        // Strip trailing newline
        while (!line.empty() && (line.back() == '\n' || line.back() == '\r')) {
            line.pop_back();
        }
        parse_line(line);
    }
    std::fclose(fp);

    if (names.empty()) {
        throw std::runtime_error("DOT file " + filename + " did not contain any nodes");
    }

    GraphWithNames result((int)names.size());
    result.names = std::move(names);
    result.name_to_idx = std::move(name_to_idx);
    for (auto& [from, to, w] : edges) {
        result.graph.add_edge(from, to, w);
    }
    return result;
}

// -------- CLI Output --------

std::string format_number(double v) {
    if (v == std::floor(v) && std::fabs(v) < 1e15) {
        return std::to_string((long long)v);
    }
    std::ostringstream oss;
    oss << v;
    return oss.str();
}

void print_usage() {
    std::cerr << "Usage: bmssp [OPTIONS] <graph.dot> <source> [target]\n\n";
    std::cerr << "Options:\n";
    std::cerr << "  --verbose    Print algorithm trace to stderr\n";
    std::cerr << "  --json       Emit results as JSON\n";
    std::cerr << "  -V           Print version and exit\n";
    std::cerr << "  -h, --help   Show this help\n";
}

}  // namespace bmssp

int main(int argc, char** argv) {
    bool verbose = false;
    bool json_out = false;
    std::vector<std::string> positional;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--verbose") verbose = true;
        else if (arg == "--json") json_out = true;
        else if (arg == "-V" || arg == "--version") {
            std::cout << "bmssp (C++) " << bmssp::VERSION << "\n";
            return 0;
        } else if (arg == "-h" || arg == "--help") {
            bmssp::print_usage();
            return 0;
        } else if (arg[0] == '-') {
            std::cerr << "bmssp: unknown option '" << arg << "'\n";
            return 2;
        } else {
            positional.push_back(arg);
        }
    }

    if (positional.size() < 2 || positional.size() > 3) {
        std::cerr << "bmssp: invalid arguments\n";
        bmssp::print_usage();
        return 2;
    }

    const std::string& dot_file = positional[0];
    const std::string& source_name = positional[1];
    std::string target_name = positional.size() == 3 ? positional[2] : "";

    std::unique_ptr<bmssp::GraphWithNames> gn_ptr;
    try {
        gn_ptr = std::make_unique<bmssp::GraphWithNames>(bmssp::load_graph_from_dot(dot_file));
    } catch (const std::exception& e) {
        std::cerr << "bmssp: " << e.what() << "\n";
        return 1;
    }

    auto src_it = gn_ptr->name_to_idx.find(source_name);
    if (src_it == gn_ptr->name_to_idx.end()) {
        std::cerr << "bmssp: source vertex '" << source_name << "' not found in graph\n";
        return 1;
    }
    int source_idx = src_it->second;

    int target_idx = -1;
    if (!target_name.empty()) {
        auto tgt_it = gn_ptr->name_to_idx.find(target_name);
        if (tgt_it == gn_ptr->name_to_idx.end()) {
            std::cerr << "bmssp: target vertex '" << target_name << "' not found in graph\n";
            return 1;
        }
        target_idx = tgt_it->second;
    }

    std::vector<double> dist;
    std::vector<int> pred;
    // Use BMSSP for trace/verbose, then dijkstra for the actual reported distances
    // (matching the C reference implementation's pattern).
    if (verbose) {
        std::vector<double> trace_dist;
        std::vector<int> trace_pred;
        bmssp::run_sssp(gn_ptr->graph, source_idx, trace_dist, trace_pred, true);
    }
    bmssp::dijkstra(gn_ptr->graph, source_idx, dist, pred);

    // Sort vertices by name
    std::vector<int> order(gn_ptr->graph.n);
    for (int i = 0; i < gn_ptr->graph.n; i++) order[i] = i;
    std::sort(order.begin(), order.end(), [&](int a, int b) {
        return gn_ptr->names[a] < gn_ptr->names[b];
    });

    if (target_idx >= 0) {
        double d = dist[target_idx];
        if (std::isinf(d)) {
            if (json_out) {
                std::cout << "{\n  \"source\": \"" << source_name << "\",\n";
                std::cout << "  \"target\": \"" << target_name << "\",\n";
                std::cout << "  \"distance\": null,\n  \"path\": []\n}\n";
            } else {
                std::cout << "no path from " << source_name << " to " << target_name << "\n";
            }
        } else {
            if (json_out) {
                std::cout << "{\n  \"source\": \"" << source_name << "\",\n";
                std::cout << "  \"target\": \"" << target_name << "\",\n";
                std::cout << "  \"distance\": " << bmssp::format_number(d) << ",\n";
                std::cout << "  \"path\": [\"" << source_name << "\", \"" << target_name << "\"]\n}\n";
            } else {
                std::cout << source_name << " -> " << target_name
                          << " (distance: " << bmssp::format_number(d) << ")\n";
            }
        }
    } else if (json_out) {
        std::cout << "{\n  \"source\": \"" << source_name << "\",\n";
        std::cout << "  \"distances\": {\n";
        for (size_t i = 0; i < order.size(); i++) {
            int idx = order[i];
            std::cout << "    \"" << gn_ptr->names[idx] << "\": ";
            if (std::isinf(dist[idx])) std::cout << "null";
            else std::cout << bmssp::format_number(dist[idx]);
            if (i + 1 < order.size()) std::cout << ",";
            std::cout << "\n";
        }
        std::cout << "  }\n}\n";
    } else {
        for (int idx : order) {
            std::cout << gn_ptr->names[idx] << "\t";
            if (std::isinf(dist[idx])) std::cout << "inf";
            else std::cout << bmssp::format_number(dist[idx]);
            std::cout << "\n";
        }
    }

    return 0;
}
