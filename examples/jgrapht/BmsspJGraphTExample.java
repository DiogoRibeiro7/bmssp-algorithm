/**
 * JGraphT integration example for BMSSP.
 *
 * Demonstrates how to convert a JGraphT DefaultDirectedWeightedGraph to the
 * BMSSP Graph type, run shortest paths, and compare against JGraphT's
 * built-in DijkstraShortestPath.
 *
 * Build (with JGraphT and the BMSSP Java implementation on the classpath):
 *   javac -cp ".:../../implementations/java:jgrapht-core-1.5.2.jar" BmsspJGraphTExample.java
 *
 * Run:
 *   java -cp ".:../../implementations/java:jgrapht-core-1.5.2.jar" BmsspJGraphTExample
 *
 * If JGraphT is not available, this file documents the integration approach
 * and contains code that can be compiled and run once dependencies are
 * installed.
 */

import java.util.*;
import org.jgrapht.Graph;
import org.jgrapht.alg.shortestpath.DijkstraShortestPath;
import org.jgrapht.graph.DefaultDirectedWeightedGraph;
import org.jgrapht.graph.DefaultWeightedEdge;

public class BmsspJGraphTExample {

    /**
     * Convert a JGraphT DefaultDirectedWeightedGraph to the BMSSP Graph type.
     */
    public static BMSSP.Graph fromJGraphT(Graph<String, DefaultWeightedEdge> jg) {
        BMSSP.Graph bg = new BMSSP.Graph();
        for (String node : jg.vertexSet()) {
            // Ensure isolated nodes are present in adjacency
            bg.addNode(node);
        }
        for (DefaultWeightedEdge e : jg.edgeSet()) {
            String u = jg.getEdgeSource(e);
            String v = jg.getEdgeTarget(e);
            double w = jg.getEdgeWeight(e);
            bg.addEdge(u, v, w);
        }
        return bg;
    }

    public static void main(String[] args) {
        System.out.println("=================================================");
        System.out.println("JGraphT -> BMSSP integration example");
        System.out.println("=================================================");

        // Build a small road-network-like graph
        Graph<String, DefaultWeightedEdge> jg =
            new DefaultDirectedWeightedGraph<>(DefaultWeightedEdge.class);

        String[] nodes = {"Home", "Bakery", "School", "Market", "Library", "Park"};
        for (String n : nodes) jg.addVertex(n);

        addEdge(jg, "Home", "Bakery", 2);
        addEdge(jg, "Home", "School", 5);
        addEdge(jg, "Bakery", "School", 1);
        addEdge(jg, "Bakery", "Market", 4);
        addEdge(jg, "School", "Library", 3);
        addEdge(jg, "Market", "Library", 2);
        addEdge(jg, "Library", "Park", 6);
        addEdge(jg, "School", "Park", 8);

        // JGraphT Dijkstra baseline
        DijkstraShortestPath<String, DefaultWeightedEdge> jgDijkstra =
            new DijkstraShortestPath<>(jg);

        // Convert to BMSSP and run
        BMSSP.Graph bg = fromJGraphT(jg);
        Map<String, Double> bmDist = BMSSP.runSSSP(bg, "Home", false);

        System.out.printf("%n%-10s%-12s%-12s%-8s%n", "node", "jgrapht", "bmssp", "match");
        System.out.println("------------------------------------------");

        String[] sorted = nodes.clone();
        Arrays.sort(sorted);
        for (String node : sorted) {
            double jgD;
            try {
                jgD = jgDijkstra.getPathWeight("Home", node);
            } catch (Exception e) {
                jgD = Double.POSITIVE_INFINITY;
            }
            double bmD = bmDist.getOrDefault(node, Double.POSITIVE_INFINITY);
            String match = (Math.abs(jgD - bmD) < 1e-9
                            || (Double.isInfinite(jgD) && Double.isInfinite(bmD)))
                           ? "yes" : "NO";
            System.out.printf("%-10s%-12s%-12s%-8s%n",
                node, formatD(jgD), formatD(bmD), match);
        }
    }

    private static void addEdge(Graph<String, DefaultWeightedEdge> g,
                                String u, String v, double w) {
        DefaultWeightedEdge e = g.addEdge(u, v);
        g.setEdgeWeight(e, w);
    }

    private static String formatD(double v) {
        if (Double.isInfinite(v)) return "inf";
        if (v == Math.floor(v)) return String.valueOf((int) v);
        return String.valueOf(v);
    }
}
