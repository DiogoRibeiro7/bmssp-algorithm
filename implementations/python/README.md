# BMSSP - Python Implementation

A Python reference implementation of BMSSP using NumPy and SciPy for
performance-friendly storage of distance arrays and sparse adjacency.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python bmssp.py [OPTIONS] <graph.dot> <source> [target]
```

Options:
- `--verbose` — print algorithm trace to stderr
- `--json` — emit results as JSON
- `-V`, `--version` — print version
- `-h`, `--help` — show help

Examples:

```bash
python bmssp.py ../../docs/examples/sample.dot A
python bmssp.py ../../docs/examples/sample.dot A H
python bmssp.py --json ../../docs/examples/sample.dot A
```

## Library API

```python
import bmssp as bm

g = bm.Graph()
g.add_edge("s", "a", 1.0)
g.add_edge("s", "b", 4.0)
g.add_edge("a", "b", 2.0)

# BMSSP (uses bounded multi-source recursion)
distances = bm.run_sssp(g, "s", verbose=False)

# Plain Dijkstra (used by the CLI for accurate output)
distances = bm.dijkstra(g, "s")
```

## Implementation Notes

- **CSR adjacency**: Uses `scipy.sparse.csr_matrix` for cache-friendly
  edge traversal. The CSR is built lazily and invalidated on edge insert.
- **NumPy distance arrays**: `d_hat` and `pred` are NumPy arrays for
  contiguous storage, mirroring the layout used by C/Rust implementations.
- **CLI behavior**: The `--verbose` flag runs BMSSP to produce a trace, then
  Dijkstra is called to produce the actual reported distances. This matches
  the C reference implementation pattern.

## Testing

```bash
python -m pytest tests/ -v
```
