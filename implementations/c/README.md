C translation of the BMSSP algorithms.

## Build and Run
```bash
gcc bmssp.c -lm -o bmssp
./bmssp graph.dot SOURCE [TARGET]
```

Pass a DOT file describing the directed graph, the source vertex name, and optionally a target vertex to print only that path. With just the source, the binary prints shortest distances and paths to every vertex discovered in the DOT file.
