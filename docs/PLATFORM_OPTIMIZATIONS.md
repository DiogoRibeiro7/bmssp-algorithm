# Platform-Specific Optimization Notes

This document covers performance characteristics and optimization opportunities
for each BMSSP implementation across different hardware and operating systems.

## C Implementation

### Compiler Flags

| Flag Set | Purpose | When to Use |
|----------|---------|-------------|
| `-O2` | Standard optimization | Default release builds |
| `-O3 -march=native` | Aggressive + native ISA | Benchmarking on known hardware |
| `-O2 -flto` | Link-time optimization | Final release binaries |
| `-Os` | Size optimization | Embedded/cache-constrained |

### Cache Behavior

The C implementation uses a contiguous adjacency list (`EdgeList` arrays), which
provides good spatial locality for edge traversal:

- **L1 cache** (32-64 KB): Holds hot nodes during `BaseCase` Dijkstra expansion.
  The `NodeDist` struct is 16 bytes, so ~2000-4000 entries fit in L1.
- **L2 cache** (256 KB - 1 MB): Critical for `FindPivots` where the working set
  is bounded by `k * |S|` nodes.
- **Prefetching**: On x86, the sequential edge scan in `add_edge` benefits from
  hardware prefetch. Consider `__builtin_prefetch` for the adjacency list of the
  next node during graph traversal.

### Profiling with perf

```bash
# CPU profiling
perf record -g ./bmssp graph.dot source
perf report

# Cache analysis
perf stat -e cache-misses,cache-references,L1-dcache-load-misses ./bmssp graph.dot source

# Branch prediction
perf stat -e branch-misses,branches ./bmssp graph.dot source
```

### Profiling with Valgrind/Cachegrind

```bash
valgrind --tool=cachegrind ./bmssp graph.dot source
cg_annotate cachegrind.out.*
```

Key areas to watch:
- `dq_pull`: Heap operations cause random access patterns
- `find_pivots`: Subtree traversal has poor locality for large graphs
- `heap_pop`: The sift-down loop is branch-heavy

### SIMD Opportunities

The current implementation does not use SIMD. Potential vectorization targets:

1. **Distance initialization**: `memset`/loop to set `dist[i] = INF` vectorizes
   naturally with `-O2`.
2. **Edge relaxation**: The inner loop comparing `d_hat[u] + w <= d_hat[v]`
   could benefit from AVX2 gather instructions for batch edge processing, but
   the random access pattern limits gains.
3. **IntArray contains**: Linear scan could use `_mm256_cmpeq_epi32` for 8-way
   parallel comparison, but sets are typically small (< 100 elements).

### Memory Layout

For graphs with n > 100K vertices, consider:
- Using `uint32_t` instead of `int` for node indices (halves memory for index arrays)
- Packing `Edge` as `{uint32_t to; float w}` (8 bytes vs 16 bytes with `double`)
- CSR (Compressed Sparse Row) format instead of adjacency lists for better
  cache utilization during sequential scans

## Go Implementation

### Garbage Collection

The Go implementation uses `map[string]` for node names, which creates GC
pressure from many small string allocations. For large graphs:

- Set `GOGC=200` or higher to reduce GC frequency at the cost of more memory
- Consider `GOMEMLIMIT` to cap total memory
- Profile with `go tool pprof` to identify allocation hotspots

```bash
# CPU profile
go test -bench=BenchmarkRunSSSP -cpuprofile=cpu.prof ./...
go tool pprof cpu.prof

# Memory profile
go test -bench=BenchmarkRunSSSP -memprofile=mem.prof ./...
go tool pprof -alloc_space mem.prof

# Trace
go test -bench=BenchmarkRunSSSP -trace=trace.out ./...
go tool trace trace.out
```

### Map vs Slice Performance

For graphs over 10K nodes, converting from `map[string]` to integer-indexed
slices can yield 2-5x speedups due to:
- Eliminating hash computation
- Better cache locality (contiguous memory)
- Reduced GC pressure (no pointer-containing maps)

### Build Tags

```bash
# Optimize for the current platform
go build -gcflags='-l -B' -ldflags='-s -w' ./cmd/bmssp/

# Profile-guided optimization (Go 1.21+)
go test -bench=. -cpuprofile=default.pgo ./...
go build -pgo=default.pgo ./cmd/bmssp/
```

## Rust Implementation

### Release Profile

The default `cargo build --release` uses `opt-level = 3`. For benchmarking:

```toml
# Cargo.toml
[profile.release]
opt-level = 3
lto = true         # link-time optimization
codegen-units = 1   # single codegen unit for better optimization
strip = true        # strip debug symbols
```

### Profiling

```bash
# Flamegraph (Linux)
cargo install flamegraph
cargo flamegraph -- graph.dot source

# perf integration
cargo build --release
perf record target/release/bmssp graph.dot source
perf report

# Criterion HTML reports
cargo bench
# Results in target/criterion/report/index.html
```

### HashSet/HashMap Performance

The Rust implementation uses `HashSet<String>` and `HashMap<String, f64>`.
For large graphs, switching to `FxHashMap`/`FxHashSet` (from the `rustc-hash`
crate) can improve performance by 20-40% due to a faster hash function:

```toml
[dependencies]
rustc-hash = "1.1"
```

### Allocation Patterns

The `BinaryHeap<NodeDist>` in DQueue allocates `String` on each push. For
performance-critical paths, consider using an arena allocator or interning
node names to avoid repeated allocation.

## Java Implementation

### JVM Tuning

```bash
# Increase heap for large graphs
java -Xmx4g -Xms4g BMSSP graph.dot source

# Enable GC logging
java -Xlog:gc* BMSSP graph.dot source

# Use G1 GC (default in modern JDKs, good for large heaps)
java -XX:+UseG1GC -XX:MaxGCPauseMillis=100 BMSSP graph.dot source

# GraalVM JIT for better peak performance
java -XX:+UseJVMCICompiler BMSSP graph.dot source
```

### Profiling with async-profiler

```bash
# CPU flamegraph
java -agentpath:/path/to/libasyncProfiler.so=start,file=cpu.html BMSSP graph.dot source

# Allocation profiling
java -agentpath:/path/to/libasyncProfiler.so=start,event=alloc,file=alloc.html BMSSP graph.dot source
```

### Collection Choices

- `HashMap<String, Double>` boxes each `Double` value. For large graphs,
  consider `Eclipse Collections` or `HPPC` for primitive-backed maps.
- `PriorityQueue` uses an array-backed binary heap, which is cache-friendly.
- `HashSet<String>` has good performance but high memory overhead (~48 bytes/entry).

### JMH Benchmarking

For rigorous benchmarking, use JMH (Java Microbenchmark Harness):

```java
@Benchmark
@Fork(2)
@Warmup(iterations = 5, time = 2)
@Measurement(iterations = 10, time = 2)
public Map<String, Double> benchmarkBMSSP() {
    return BMSSP.runSSSP(graph, "source", false);
}
```

## Fortran Implementation

### Compiler Flags

| Compiler | Flags | Notes |
|----------|-------|-------|
| gfortran | `-O2 -march=native` | Good default |
| gfortran | `-O3 -ffast-math -funroll-loops` | Aggressive (may change numerics) |
| ifort/ifx | `-O2 -xHost` | Intel-optimized, auto-vectorization |

### Array Layout

Fortran uses column-major order. The `edges(MAX_NODES, MAX_EDGES)` array stores
edges for each node in columns, which means scanning edges of a single node
accesses non-contiguous memory. Consider transposing to `edges(MAX_EDGES, MAX_NODES)`
for better cache behavior during edge traversal.

### Static Arrays

The current implementation uses fixed-size arrays (`MAX_NODES = 1000`). For
large graphs, switch to `allocatable` arrays:

```fortran
type :: Graph
    integer :: n
    integer, allocatable :: deg(:)
    type(Edge), allocatable :: edges(:,:)
end type Graph
```

## Julia Implementation

### Compilation and Startup

Julia has significant first-run compilation overhead. For benchmarking:

```julia
# Warm up the JIT
using BenchmarkTools
@benchmark run_sssp(graph, source)

# Precompile for faster startup
using PackageCompiler
create_app("BMSSPAlgorithm", "bmssp_compiled")
```

### Type Stability

The current implementation uses `Any` types in `Graph.adj` and `DQueue`. For
performance, specialize to concrete types:

```julia
# Instead of Dict{Any, Vector{Tuple{Any, Float64}}}
# Use Dict{String, Vector{Tuple{String, Float64}}}
```

Type instability forces Julia to box values and use dynamic dispatch, which
can be 10-100x slower than type-stable code. Check with:

```julia
@code_warntype run_sssp(graph, "source")
```

### Profiling

```julia
using Profile
@profile run_sssp(graph, source)
Profile.print()

# Allocation tracking
@time run_sssp(graph, source)
@allocated run_sssp(graph, source)
```

## Cross-Platform Notes

### x86-64 vs ARM64

- **x86-64**: Benefits from out-of-order execution and large reorder buffers.
  The branch-heavy `heap_pop`/`heap_push` code performs well due to branch
  prediction. Use `-march=native` to enable AVX2 for vectorized initialization.

- **ARM64 (Apple Silicon, Graviton)**: Wider issue width and better
  branch prediction than older x86. The `cmp`/`b.lt` pattern in edge relaxation
  maps well to ARM's conditional execution. Apple Silicon's unified memory
  architecture benefits the random access patterns in graph traversal.

### Memory Bandwidth

For large graphs (n > 10^6), memory bandwidth becomes the bottleneck:

- **DDR4** (~25-50 GB/s): Limits throughput to ~200M-400M random 8-byte reads/s
- **DDR5** (~50-80 GB/s): ~400M-600M random reads/s
- **NUMA**: On multi-socket systems, ensure the graph data and distance arrays
  are allocated on the same NUMA node. Use `numactl --localalloc` on Linux.

### Operating System

- **Linux**: Best for benchmarking. Use `taskset` to pin to a single core,
  `cpupower frequency-set -g performance` to disable frequency scaling.
- **macOS**: Good performance but `clock_gettime` resolution varies.
  Use `mach_absolute_time` for precise timing.
- **Windows**: Use `QueryPerformanceCounter` for timing. Consider WSL2
  for consistent cross-platform comparisons.

### Recommended Benchmark Environment

```bash
# Linux setup for reproducible benchmarks
sudo cpupower frequency-set -g performance    # fixed CPU frequency
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space  # disable ASLR
taskset -c 0 ./bmssp graph.dot source          # pin to core 0
```

---

See also:
- [PARAMETER_SENSITIVITY.md](PARAMETER_SENSITIVITY.md) for algorithm parameter tuning
- [PERFORMANCE_ANALYSIS.md](../benchmarks/PERFORMANCE_ANALYSIS.md) for interpreting benchmark results
