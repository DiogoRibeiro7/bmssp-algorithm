# Integration Examples

Adapter examples showing how to use BMSSP with popular graph libraries.

| Example | Library | Language | Run |
|---------|---------|----------|-----|
| [networkx/](networkx/) | NetworkX | Python | `python bmssp_networkx.py` |
| [petgraph/](petgraph/) | petgraph | Rust | `cargo run --release` |
| [jgrapht/](jgrapht/) | JGraphT | Java | `javac` + `java` (see below) |

## NetworkX (Python)

The adapter converts a `networkx.DiGraph` to the BMSSP `Graph` type, runs
shortest paths, and verifies the result against `nx.single_source_dijkstra_path_length`.

```bash
cd networkx
python bmssp_networkx.py
```

## petgraph (Rust)

Uses `petgraph::graph::DiGraph<&str, f64>` and converts edges by name. Compares
against `petgraph::algo::dijkstra`.

```bash
cd petgraph
cargo run --release
```

## JGraphT (Java)

Uses `DefaultDirectedWeightedGraph<String, DefaultWeightedEdge>`. Requires
JGraphT on the classpath.

```bash
# Download jgrapht-core jar
curl -L -o jgrapht-core-1.5.2.jar \
  https://repo1.maven.org/maven2/org/jgrapht/jgrapht-core/1.5.2/jgrapht-core-1.5.2.jar

cd jgrapht
javac -cp ".:../../implementations/java:jgrapht-core-1.5.2.jar" BmsspJGraphTExample.java
java -cp ".:../../implementations/java:jgrapht-core-1.5.2.jar" BmsspJGraphTExample
```

## Adapter Pattern

All three examples follow the same pattern:

1. **Iterate nodes** of the source graph and ensure each is registered in
   the BMSSP graph (in case there are isolated nodes).
2. **Iterate edges** and call `addEdge(u, v, weight)` on the BMSSP graph,
   converting node identities to strings.
3. **Run BMSSP** (or its `dijkstra` companion) and return the resulting
   distances dict.

This is the simplest possible adapter — it copies the graph structure once.
For library users who need repeated queries on the same graph, the adapter
can be cached.
