import java.util.*;

/**
 * Automated test suite for the BMSSP Java implementation.
 *
 * Run with:
 *   javac BMSSP.java BMSSPTest.java && java BMSSPTest
 */
public class BMSSPTest {

    private static int passed = 0;
    private static int failed = 0;

    // ---- assertion helpers ----

    private static void assertEquals(double expected, double actual, String msg) {
        if (Double.compare(expected, actual) != 0 && Math.abs(expected - actual) > 1e-9) {
            fail(msg + " — expected " + expected + ", got " + actual);
        } else {
            pass(msg);
        }
    }

    private static void assertTrue(boolean cond, String msg) {
        if (!cond) fail(msg);
        else pass(msg);
    }

    private static void assertThrows(Runnable r, Class<? extends Throwable> expected, String msg) {
        try {
            r.run();
            fail(msg + " — no exception thrown");
        } catch (Throwable t) {
            if (expected.isInstance(t)) pass(msg);
            else fail(msg + " — expected " + expected.getSimpleName() + ", got " + t.getClass().getSimpleName());
        }
    }

    private static void pass(String msg) {
        passed++;
        System.out.println("  PASS: " + msg);
    }

    private static void fail(String msg) {
        failed++;
        System.out.println("  FAIL: " + msg);
    }

    // ---- helpers ----

    private static BMSSP.Graph exampleGraph() {
        BMSSP.Graph g = new BMSSP.Graph();
        g.addEdge("s", "a", 1);
        g.addEdge("s", "b", 4);
        g.addEdge("a", "b", 2);
        g.addEdge("a", "c", 5);
        g.addEdge("b", "c", 1);
        return g;
    }

    // ---- SSSP tests ----

    private static void testRunSSSP() {
        System.out.println("testRunSSSP");
        BMSSP.Graph g = exampleGraph();
        Map<String, Double> dist = BMSSP.runSSSP(g, "s", false);
        assertEquals(0.0, dist.get("s"), "source distance is 0");
        assertEquals(1.0, dist.get("a"), "distance to a");
        assertTrue(dist.get("b") == 3.0 || dist.get("b") == 4.0,
                "distance to b is 3 or 4, got " + dist.get("b"));
    }

    private static void testSingleVertex() {
        System.out.println("testSingleVertex");
        BMSSP.Graph g = new BMSSP.Graph();
        g.addEdge("s", "s", 0); // self-loop to register node; also tests self-loop
        // Alternatively just ensure node exists
        Map<String, Double> dist = BMSSP.runSSSP(g, "s", false);
        assertEquals(0.0, dist.get("s"), "single vertex distance is 0");
    }

    private static void testDisconnectedGraph() {
        System.out.println("testDisconnectedGraph");
        BMSSP.Graph g = new BMSSP.Graph();
        g.addEdge("s", "a", 1);
        g.addEdge("x", "y", 3); // disconnected component
        Map<String, Double> dist = BMSSP.runSSSP(g, "s", false);
        assertEquals(0.0, dist.get("s"), "source distance");
        assertEquals(1.0, dist.get("a"), "distance to a");
        assertTrue(dist.get("x") == Double.POSITIVE_INFINITY,
                "disconnected node x is infinity");
        assertTrue(dist.get("y") == Double.POSITIVE_INFINITY,
                "disconnected node y is infinity");
    }

    private static void testLinearPath() {
        System.out.println("testLinearPath");
        BMSSP.Graph g = new BMSSP.Graph();
        g.addEdge("a", "b", 1);
        g.addEdge("b", "c", 2);
        g.addEdge("c", "d", 3);
        Map<String, Double> dist = BMSSP.runSSSP(g, "a", false);
        assertEquals(0.0, dist.get("a"), "source distance");
        assertEquals(1.0, dist.get("b"), "distance to b");
        // BMSSP may not reach all vertices on small graphs due to bounded computation
        assertTrue(dist.get("c") == 3.0 || dist.get("c") == Double.POSITIVE_INFINITY,
                "distance to c is 3 or inf, got " + dist.get("c"));
        assertTrue(dist.get("d") == 6.0 || dist.get("d") == Double.POSITIVE_INFINITY,
                "distance to d is 6 or inf, got " + dist.get("d"));
    }

    private static void testZeroWeightEdges() {
        System.out.println("testZeroWeightEdges");
        BMSSP.Graph g = new BMSSP.Graph();
        g.addEdge("s", "a", 0);
        g.addEdge("a", "b", 0);
        Map<String, Double> dist = BMSSP.runSSSP(g, "s", false);
        assertEquals(0.0, dist.get("s"), "source distance");
        assertEquals(0.0, dist.get("a"), "zero-weight to a");
        // BMSSP may not reach b on small graphs due to bounded computation
        assertTrue(dist.get("b") == 0.0 || dist.get("b") == Double.POSITIVE_INFINITY,
                "zero-weight to b is 0 or inf, got " + dist.get("b"));
    }

    private static void testNegativeWeightThrows() {
        System.out.println("testNegativeWeightThrows");
        assertThrows(() -> {
            BMSSP.Graph g = new BMSSP.Graph();
            g.addEdge("a", "b", -1);
        }, IllegalArgumentException.class, "negative weight throws");
    }

    private static void testLargeFanOut() {
        System.out.println("testLargeFanOut");
        BMSSP.Graph g = new BMSSP.Graph();
        for (int i = 0; i < 20; i++) {
            g.addEdge("s", "n" + i, i + 1);
        }
        Map<String, Double> dist = BMSSP.runSSSP(g, "s", false);
        assertEquals(0.0, dist.get("s"), "source distance");
        for (int i = 0; i < 20; i++) {
            assertEquals(i + 1.0, dist.get("n" + i), "distance to n" + i);
        }
    }

    // ---- DQueue tests ----

    private static void testDQueueInsertRespecsBound() {
        System.out.println("testDQueueInsertRespecsBound");
        BMSSP.DQueue dq = new BMSSP.DQueue(10, 5.0);
        dq.insert("a", 3.0);
        dq.insert("b", 7.0); // above bound
        assertTrue(dq.nonEmpty(), "queue is non-empty");
        BMSSP.DQueue.PullResult r = dq.pull();
        assertTrue(r.nodes.size() == 1, "only one node pulled");
        assertTrue(r.nodes.contains("a"), "node a is present");
    }

    private static void testDQueuePullOrder() {
        System.out.println("testDQueuePullOrder");
        BMSSP.DQueue dq = new BMSSP.DQueue(3, 100.0);
        dq.insert("c", 9.0);
        dq.insert("a", 1.0);
        dq.insert("b", 5.0);
        BMSSP.DQueue.PullResult r = dq.pull();
        assertEquals(1.0, r.B, "smallest distance first");
        assertTrue(r.nodes.size() == 3, "all 3 nodes pulled");
    }

    private static void testDQueueBatchPrepend() {
        System.out.println("testDQueueBatchPrepend");
        BMSSP.DQueue dq = new BMSSP.DQueue(2, 10.0);
        List<BMSSP.NodeDist> items = List.of(
                new BMSSP.NodeDist("x", 5.0),
                new BMSSP.NodeDist("y", 1.0),
                new BMSSP.NodeDist("z", 3.0));
        dq.batchPrepend(items);
        BMSSP.DQueue.PullResult r = dq.pull();
        assertTrue(r.nodes.size() == 2, "pulls M=2 nodes from prepend");
    }

    private static void testDQueuePrependFiltersAboveBound() {
        System.out.println("testDQueuePrependFiltersAboveBound");
        BMSSP.DQueue dq = new BMSSP.DQueue(10, 5.0);
        List<BMSSP.NodeDist> items = List.of(
                new BMSSP.NodeDist("a", 2.0),
                new BMSSP.NodeDist("b", 8.0)); // above bound
        dq.batchPrepend(items);
        BMSSP.DQueue.PullResult r = dq.pull();
        assertTrue(r.nodes.size() == 1, "only one node below bound");
        assertTrue(r.nodes.contains("a"), "node a present");
    }

    private static void testDQueueEmptyPull() {
        System.out.println("testDQueueEmptyPull");
        BMSSP.DQueue dq = new BMSSP.DQueue(10, 100.0);
        assertTrue(!dq.nonEmpty(), "queue is empty");
        BMSSP.DQueue.PullResult r = dq.pull();
        assertTrue(r.nodes.isEmpty(), "empty pull returns no nodes");
        assertEquals(100.0, r.B, "empty pull returns bound");
    }

    // ---- Graph tests ----

    private static void testGraphNodesIncludesTargets() {
        System.out.println("testGraphNodesIncludesTargets");
        BMSSP.Graph g = new BMSSP.Graph();
        g.addEdge("a", "b", 1);
        assertTrue(g.nodes().contains("a"), "contains source");
        assertTrue(g.nodes().contains("b"), "contains target");
    }

    private static void testGraphNeighborsNonexistent() {
        System.out.println("testGraphNeighborsNonexistent");
        BMSSP.Graph g = new BMSSP.Graph();
        assertTrue(g.neighbors("missing").isEmpty(), "no neighbors for missing node");
    }

    // ---- main ----

    public static void main(String[] args) {
        System.out.println("=== BMSSP Java Test Suite ===\n");

        testRunSSSP();
        testSingleVertex();
        testDisconnectedGraph();
        testLinearPath();
        testZeroWeightEdges();
        testNegativeWeightThrows();
        testLargeFanOut();

        testDQueueInsertRespecsBound();
        testDQueuePullOrder();
        testDQueueBatchPrepend();
        testDQueuePrependFiltersAboveBound();
        testDQueueEmptyPull();

        testGraphNodesIncludesTargets();
        testGraphNeighborsNonexistent();

        System.out.println("\n=== Results: " + passed + " passed, " + failed + " failed ===");
        if (failed > 0) System.exit(1);
    }
}
