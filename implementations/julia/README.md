# Julia Implementation of BMSSP Algorithm

This directory contains a Julia implementation of the BMSSP (Breaking the Sorting Barrier for Directed Single-Source Shortest Paths) algorithm from the paper [arXiv:2504.17033v2](https://arxiv.org/abs/2504.17033).

## Files

- `BMSSP.jl` - Main implementation file
- `test_bmssp.jl` - Test suite
- `Project.toml` - Julia project definition (optional)

## Requirements

- Julia 1.6+ (tested with Julia 1.8)
- DataStructures.jl package

To install the required package:

```julia
using Pkg
Pkg.add("DataStructures")
```

## Usage

### Basic Example

```julia
include("BMSSP.jl")

# Create a graph
g = Graph()
add_edge!(g, "s", "a", 1.0)
add_edge!(g, "s", "b", 4.0)
add_edge!(g, "a", "b", 2.0)
add_edge!(g, "a", "c", 5.0)
add_edge!(g, "b", "c", 1.0)

# Run SSSP
distances = run_sssp(g, "s")

# Print results
for (node, distance) in sort(collect(distances))
    if distance == Inf
        println("$node: ∞")
    else
        println("$node: $distance")
    end
end
```

### Running the Example

```bash
julia BMSSP.jl
```

### Running Tests

```bash
julia test_bmssp.jl
```

## Implementation Details

This Julia implementation includes:

1. **Graph Structure**: Adjacency list representation with support for any type of node identifiers
2. **DQueue**: Specialized queue structure for batch operations with distance bounds
3. **FindPivots**: Implementation of Lemma 3.2 from the paper for pivot selection
4. **BaseCase**: Small-instance solver for bottom level of recursion
5. **BMSSP**: Main recursive algorithm

## Algorithm Parameters

The implementation automatically calculates these parameters based on graph size (n):

- `k = ⌊log^(1/3) n⌋`: Pivot selection parameter
- `t = ⌊log^(2/3) n⌋`: Recursion branching factor
- `l = ⌈log n / t⌉`: Recursion levels

## Notes

- This is a research algorithm implementation demonstrating the theoretical properties of BMSSP
- Due to bounded exploration, BMSSP may not compute complete shortest path trees
- For small graphs, the algorithm overhead may exceed the theoretical benefits
- Parameters are tuned for asymptotic complexity (O(m log^(2/3) n)), not practical performance on small graphs

## Performance

On large sparse graphs, BMSSP theoretically outperforms Dijkstra's O(m + n log n) barrier,
achieving O(m log^(2/3) n) time complexity.

For benchmarking results, refer to `../benchmarks/PERFORMANCE_ANALYSIS.md`.
