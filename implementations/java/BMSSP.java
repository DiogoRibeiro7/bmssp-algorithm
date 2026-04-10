import java.io.*;
import java.util.*;
import java.util.regex.*;

/**
 * BMSSP – Breaking the Sorting Barrier for Directed Single-Source Shortest Paths
 *
 * This is a Java reference implementation following the paper:
 *   Breaking the Sorting Barrier for Directed Single-Source Shortest Paths
 *   David H. Yu et al., 2025.
 *
 * The implementation mirrors the Python version in this repository and
 * contains the core algorithms:
 *   - Graph data structure
 *   - DQueue (Lemma 3.3)
 *   - baseCase (small-instance solver)
 *   - findPivots (Lemma 3.2)
 *   - bmssp (Algorithm 3)
 *
 * The code is intentionally verbose to match the clarity of the Python
 * reference. Nodes are represented using strings for simplicity, but the
 * implementation could be generalized with generics if needed.
 */
public class BMSSP {

    /** Graph represents a directed graph with non-negative edge weights. */
    public static class Graph {
        private final Map<String, List<Edge>> adj = new HashMap<>();

        /** Edge record storing neighbor and weight. */
        private static class Edge {
            String to;
            double w;
            Edge(String to, double w) { this.to = to; this.w = w; }
        }

        /** Adds a directed edge u->v with weight w. */
        public void addEdge(String u, String v, double w) {
            if (w < 0) throw new IllegalArgumentException("Only non-negative weights allowed");
            adj.computeIfAbsent(u, k -> new ArrayList<>()).add(new Edge(v, w));
            adj.computeIfAbsent(v, k -> new ArrayList<>()); // ensure v in adjacency
        }

        /** Returns neighbors of node u. */
        public List<Edge> neighbors(String u) {
            return adj.getOrDefault(u, Collections.emptyList());
        }

        public Set<String> nodes() { return adj.keySet(); }
    }

    /** Simple container for node-distance pairs used throughout the algorithm. */
    public static class NodeDist implements Comparable<NodeDist> {
        String node;
        double dist;
        NodeDist(String n, double d) { node = n; dist = d; }
        public int compareTo(NodeDist o) { return Double.compare(dist, o.dist); }
    }

    /**
     * DQueue is a specialized queue structure supporting batch operations
     * and bounded by distance threshold B.
     */
    public static class DQueue {
        private final int M;           // max nodes to pull per batch
        private final double B;        // distance threshold
        private final PriorityQueue<NodeDist> data;
        private final List<NodeDist> prepend;

        public DQueue(int M, double B) {
            this.M = M; this.B = B;
            data = new PriorityQueue<>();
            prepend = new ArrayList<>();
        }

        /** Insert node with distance if below bound B. */
        public void insert(String node, double dist) {
            if (dist >= B) return;
            data.add(new NodeDist(node, dist));
        }

        /** Batch prepend items if below bound B. */
        public void batchPrepend(List<NodeDist> items) {
            for (NodeDist nd : items) {
                if (nd.dist < B) prepend.add(nd);
            }
            Collections.sort(prepend);
        }

        /** Pull up to M nodes grouped by their distance. */
        public PullResult pull() {
            if (!prepend.isEmpty()) {
                List<NodeDist> group = new ArrayList<>();
                int m = Math.min(M, prepend.size());
                for (int i = 0; i < m; i++) group.add(prepend.remove(0));
                double Bi = group.get(0).dist;
                Set<String> nodes = new HashSet<>();
                for (NodeDist nd : group) nodes.add(nd.node);
                return new PullResult(Bi, nodes);
            }
            if (data.isEmpty()) return new PullResult(B, new HashSet<>());
            List<NodeDist> out = new ArrayList<>();
            while (!data.isEmpty() && out.size() < M) {
                out.add(data.poll());
            }
            double Bi = out.get(0).dist;
            Set<String> nodes = new HashSet<>();
            for (NodeDist nd : out) nodes.add(nd.node);
            return new PullResult(Bi, nodes);
        }

        /** Check if queue contains any nodes. */
        public boolean nonEmpty() {
            return !(data.isEmpty() && prepend.isEmpty());
        }

        /** Simple container for pull result. */
        public static class PullResult {
            public final double B;
            public final Set<String> nodes;
            PullResult(double B, Set<String> nodes) { this.B = B; this.nodes = nodes; }
        }
    }

    // -------- Result containers for API consistency --------

    /** Container for pivot selection results. */
    static class PivotResult {
        final Set<String> P;
        final Set<String> W;
        PivotResult(Set<String> p, Set<String> w) { this.P = p; this.W = w; }
    }

    /** Container for base-case results. */
    static class BaseCaseResult {
        final double B;
        final Set<String> U;
        BaseCaseResult(double B, Set<String> U) { this.B = B; this.U = U; }
    }

    /** Container for recursive BMSSP results. */
    static class BMSSPResult {
        final double B;
        final Set<String> U;
        BMSSPResult(double B, Set<String> U) { this.B = B; this.U = U; }
    }

    /** Base case: expand nodes until reaching k+1 nodes or heap exhausted. */
    public static BaseCaseResult baseCase(
            Graph graph, double B, Set<String> S, Map<String, Double> dHat,
            Set<String> complete, int k, boolean verbose) {
        Iterator<String> it = S.iterator();
        String x = it.next();
        Set<String> U0 = new HashSet<>(); U0.add(x);
        PriorityQueue<NodeDist> H = new PriorityQueue<>();
        H.add(new NodeDist(x, dHat.get(x)));
        Set<String> visited = new HashSet<>();
        if (verbose) System.out.println("base_case: start from " + x + " B=" + B);

        while (!H.isEmpty() && U0.size() < k + 1) {
            NodeDist nd = H.poll();
            String u = nd.node; double du = nd.dist;
            if (visited.contains(u)) continue;
            visited.add(u); U0.add(u); complete.add(u);
            for (Graph.Edge e : graph.neighbors(u)) {
                double alt = du + e.w;
                if (alt <= dHat.get(e.to) && alt < B) {
                    dHat.put(e.to, alt);
                    H.add(new NodeDist(e.to, alt));
                }
            }
        }
        if (U0.size() <= k) {
            if (verbose) System.out.println("base_case: early termination |U0| <= k");
            return new BaseCaseResult(B, U0);
        } else {
            double Bprime = Double.NEGATIVE_INFINITY;
            for (String v : U0) {
                Bprime = Math.max(Bprime, dHat.get(v));
            }
            if (verbose) System.out.println("base_case: computed B'=" + Bprime);
            Set<String> subset = new HashSet<>();
            for (String v : U0) if (dHat.get(v) < Bprime) subset.add(v);
            return new BaseCaseResult(Bprime, subset);
        }
    }

    /** Find pivots and witnesses as in Lemma 3.2. */
    public static PivotResult findPivots(
            Graph graph, double B, Set<String> S, Map<String, Double> dHat,
            Set<String> complete, int k, boolean verbose) {
        Set<String> W = new HashSet<>(S);
        Set<String> Wprev = new HashSet<>(S);
        if (verbose)
            System.out.println("find_pivots: start |S|=" + S.size() + " B=" + B);

        for (int iter = 1; iter <= k; iter++) {
            Set<String> Wi = new HashSet<>();
            for (String u : Wprev) {
                double du = dHat.get(u);
                if (du >= B) continue;
                for (Graph.Edge e : graph.neighbors(u)) {
                    double alt = du + e.w;
                    if (alt <= dHat.get(e.to)) {
                        dHat.put(e.to, alt);
                        if (alt < B) Wi.add(e.to);
                    }
                }
            }
            W.addAll(Wi);
            if (W.size() > k * S.size()) {
                if (verbose)
                    System.out.println("find_pivots: early termination |W| > k*|S|");
                return new PivotResult(new HashSet<>(S), W);
            }
            Wprev = Wi;
        }

        Map<String, List<String>> children = new HashMap<>();
        Map<String, Integer> indeg = new HashMap<>();
        for (String u : W) {
            children.put(u, new ArrayList<>());
            indeg.put(u, 0);
        }
        for (String u : W) {
            double du = dHat.get(u);
            for (Graph.Edge e : graph.neighbors(u)) {
                String v = e.to; double w = e.w;
                if (W.contains(v) && Math.abs(dHat.get(v) - (du + w)) < 1e-12) {
                    children.get(u).add(v);
                    indeg.put(v, indeg.get(v) + 1);
                }
            }
        }

        Set<String> pivots = new HashSet<>();
        for (String u : S) {
            if (indeg.getOrDefault(u, 0) == 0 && subtreeSize(u, children, new HashSet<>()) >= k) {
                pivots.add(u);
            }
        }
        if (verbose) System.out.println("find_pivots: pivots=" + pivots);
        return new PivotResult(pivots, W);
    }

    private static int subtreeSize(String u, Map<String, List<String>> children, Set<String> seen) {
        if (seen.contains(u)) return 0;
        seen.add(u);
        int size = 1;
        for (String v : children.getOrDefault(u, Collections.emptyList())) {
            size += subtreeSize(v, children, seen);
        }
        seen.remove(u);
        return size;
    }

    /** Recursive BMSSP algorithm. */
    public static BMSSPResult bmssp(
            Graph graph, int l, double B, Set<String> S, Map<String, Double> dHat,
            Set<String> complete, int k, int t, boolean verbose) {
        if (verbose)
            System.out.println("bmssp: level=" + l + " B=" + B + " |S|=" + S.size());
        if (l == 0) {
            BaseCaseResult bc = baseCase(graph, B, S, dHat, complete, k, verbose);
            if (verbose)
                System.out.println("bmssp: base case returns B=" + bc.B + " |U|=" + bc.U.size());
            return new BMSSPResult(bc.B, bc.U);
        }
        PivotResult pw = findPivots(graph, B, S, dHat, complete, k, verbose);
        Set<String> P = pw.P; Set<String> W = pw.W;
        if (verbose) System.out.println("bmssp: pivots=" + P);
        int M = (int)Math.pow(2, (l - 1) * t);
        DQueue D = new DQueue(M, B);
        for (String x : P) D.insert(x, dHat.get(x));
        Set<String> U = new HashSet<>();
        double B0Prime = P.stream().mapToDouble(dHat::get).min().orElse(B);
        if (verbose) System.out.println("bmssp: B0'=" + B0Prime);
        while (U.size() < k * Math.pow(2, l * t) && D.nonEmpty()) {
            DQueue.PullResult pr = D.pull();
            double Bi = pr.B; Set<String> Si = pr.nodes;
            BMSSPResult rec = bmssp(graph, l - 1, Bi, Si, dHat, complete, k, t, verbose);
            double Bprime_i = rec.B; Set<String> Ui = rec.U; U.addAll(Ui);
            List<NodeDist> K = new ArrayList<>();
            for (String u : Ui) {
                for (Graph.Edge e : graph.neighbors(u)) {
                    double alt = dHat.get(u) + e.w;
                    if (alt <= dHat.get(e.to)) {
                        dHat.put(e.to, alt);
                        if (alt >= Bi && alt < B) D.insert(e.to, alt);
                        else if (alt >= Bprime_i && alt < Bi) K.add(new NodeDist(e.to, alt));
                    }
                }
            }
            List<NodeDist> prependItems = new ArrayList<>(K);
            for (String x : Si) {
                double dx = dHat.get(x);
                if (dx >= Bprime_i && dx < Bi) prependItems.add(new NodeDist(x, dx));
            }
            D.batchPrepend(prependItems);
        }
        if (verbose) {
            String reason = "condition";
            if (U.size() >= k * Math.pow(2, l * t)) reason = "U size reached";
            else if (!D.nonEmpty()) reason = "queue empty";
            System.out.println("bmssp: terminating loop due to " + reason);
        }
        double Bprime = Math.min(B0Prime, B);
        for (String x : W) if (dHat.get(x) < Bprime) U.add(x);
        complete.addAll(U);
        if (verbose)
            System.out.println("bmssp: returning B=" + Bprime + " |U|=" + U.size());
        return new BMSSPResult(Bprime, U);
    }

    /** Runs SSSP from a single source using BMSSP. */
    public static Map<String, Double> runSSSP(Graph g, String source, boolean verbose) {
        int n = g.nodes().size();
        double log2n = Math.log(n) / Math.log(2);
        int k = (int)Math.max(1.0, Math.cbrt(log2n));
        int t = (int)Math.max(1.0, Math.pow(log2n, 2.0/3.0));
        int l = (int)Math.ceil(log2n / t);
        Map<String, Double> dHat = new HashMap<>();
        for (String v : g.nodes()) dHat.put(v, Double.POSITIVE_INFINITY);
        dHat.put(source, 0.0);
        Set<String> complete = new HashSet<>();
        complete.add(source);
        Set<String> S = new HashSet<>();
        S.add(source);
        bmssp(g, l, Double.POSITIVE_INFINITY, S, dHat, complete, k, t, verbose);
        return dHat;
    }

    private static final String VERSION = "0.1.0";

    /** Load a directed weighted graph from a DOT file. */
    public static Graph loadGraphFromDOT(String filename) throws IOException {
        Graph g = new Graph();
        Pattern edgePattern = Pattern.compile(
            "^\\s*(\\S+)\\s*->\\s*(\\S+)\\s*(?:\\[.*label\\s*=\\s*([0-9.eE+-]+).*\\])?\\s*;?\\s*$");
        Pattern nodePattern = Pattern.compile("^\\s*(\\w+)\\s*;\\s*$");

        try (BufferedReader br = new BufferedReader(new FileReader(filename))) {
            String line;
            int lineNum = 0;
            while ((line = br.readLine()) != null) {
                lineNum++;
                String trimmed = line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("//")
                        || trimmed.startsWith("digraph") || trimmed.equals("}")) {
                    continue;
                }
                Matcher edgeMatch = edgePattern.matcher(trimmed);
                if (edgeMatch.matches()) {
                    String from = edgeMatch.group(1);
                    String to = edgeMatch.group(2);
                    double weight = 1.0;
                    if (edgeMatch.group(3) != null) {
                        weight = Double.parseDouble(edgeMatch.group(3));
                    }
                    g.addEdge(from, to, weight);
                } else {
                    Matcher nodeMatch = nodePattern.matcher(trimmed);
                    if (nodeMatch.matches()) {
                        String node = nodeMatch.group(1);
                        g.adj.computeIfAbsent(node, k -> new ArrayList<>());
                    }
                }
            }
        }
        if (g.nodes().isEmpty()) {
            throw new IOException("DOT file " + filename + " did not contain any nodes");
        }
        return g;
    }

    private static String formatNumber(double v) {
        if (v == Math.floor(v) && Math.abs(v) < 1e15) {
            return String.valueOf((long) v);
        }
        return String.valueOf(v);
    }

    /** CLI entry point following CLI_SPEC.md. */
    public static void main(String[] args) {
        boolean verbose = false;
        boolean jsonOut = false;
        List<String> positional = new ArrayList<>();

        for (String arg : args) {
            switch (arg) {
                case "--verbose": verbose = true; break;
                case "--json": jsonOut = true; break;
                case "-V": case "--version":
                    System.out.println("bmssp (Java) " + VERSION);
                    System.exit(0);
                    break;
                case "-h": case "--help":
                    System.err.println("Usage: java BMSSP [OPTIONS] <graph.dot> <source> [target]");
                    System.exit(0);
                    break;
                default:
                    if (arg.startsWith("-")) {
                        System.err.println("bmssp: unknown option '" + arg + "'");
                        System.exit(2);
                    }
                    positional.add(arg);
            }
        }

        if (positional.size() < 2 || positional.size() > 3) {
            System.err.println("bmssp: invalid arguments");
            System.err.println("Usage: java BMSSP [OPTIONS] <graph.dot> <source> [target]");
            System.exit(2);
        }

        String dotFile = positional.get(0);
        String source = positional.get(1);
        String target = positional.size() == 3 ? positional.get(2) : null;

        Graph graph;
        try {
            graph = loadGraphFromDOT(dotFile);
        } catch (IOException e) {
            System.err.println("bmssp: " + e.getMessage());
            System.exit(1);
            return;
        }

        if (!graph.nodes().contains(source)) {
            System.err.println("bmssp: source vertex '" + source + "' not found in graph");
            System.exit(1);
        }
        if (target != null && !graph.nodes().contains(target)) {
            System.err.println("bmssp: target vertex '" + target + "' not found in graph");
            System.exit(1);
        }

        Map<String, Double> dist = runSSSP(graph, source, verbose);
        TreeMap<String, Double> sorted = new TreeMap<>(dist);

        if (target != null) {
            double d = dist.getOrDefault(target, Double.POSITIVE_INFINITY);
            if (Double.isInfinite(d)) {
                if (jsonOut) {
                    System.out.println("{");
                    System.out.println("  \"source\": \"" + source + "\",");
                    System.out.println("  \"target\": \"" + target + "\",");
                    System.out.println("  \"distance\": null,");
                    System.out.println("  \"path\": []");
                    System.out.println("}");
                } else {
                    System.out.println("no path from " + source + " to " + target);
                }
            } else {
                if (jsonOut) {
                    System.out.println("{");
                    System.out.println("  \"source\": \"" + source + "\",");
                    System.out.println("  \"target\": \"" + target + "\",");
                    System.out.println("  \"distance\": " + formatNumber(d) + ",");
                    System.out.println("  \"path\": [\"" + source + "\", \"" + target + "\"]");
                    System.out.println("}");
                } else {
                    System.out.println(source + " -> " + target + " (distance: " + formatNumber(d) + ")");
                }
            }
        } else if (jsonOut) {
            System.out.println("{");
            System.out.println("  \"source\": \"" + source + "\",");
            System.out.println("  \"distances\": {");
            int i = 0;
            for (Map.Entry<String, Double> entry : sorted.entrySet()) {
                String comma = (i + 1 < sorted.size()) ? "," : "";
                if (Double.isInfinite(entry.getValue())) {
                    System.out.println("    \"" + entry.getKey() + "\": null" + comma);
                } else {
                    System.out.println("    \"" + entry.getKey() + "\": " + formatNumber(entry.getValue()) + comma);
                }
                i++;
            }
            System.out.println("  }");
            System.out.println("}");
        } else {
            for (Map.Entry<String, Double> entry : sorted.entrySet()) {
                if (Double.isInfinite(entry.getValue())) {
                    System.out.println(entry.getKey() + "\tinf");
                } else {
                    System.out.println(entry.getKey() + "\t" + formatNumber(entry.getValue()));
                }
            }
        }
    }
}
