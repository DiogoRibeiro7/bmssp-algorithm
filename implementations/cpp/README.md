# BMSSP - C++ Implementation

A modern C++17 reference implementation of BMSSP (Breaking the Sorting Barrier
for Directed Single-Source Shortest Paths) by Duan et al., 2025.

## Build

```bash
make            # release build with -O2
make debug      # debug build with -O0 -g
```

Or directly:

```bash
g++ -Wall -Wextra -std=c++17 -O2 bmssp.cpp -o bmssp
```

## Usage

```bash
./bmssp [OPTIONS] <graph.dot> <source> [target]
```

Options:
- `--verbose` — print algorithm trace to stderr
- `--json` — emit results as JSON
- `-V`, `--version` — print version
- `-h`, `--help` — show help

Examples:

```bash
./bmssp ../../docs/examples/sample.dot A
./bmssp ../../docs/examples/sample.dot A H
./bmssp --json ../../docs/examples/sample.dot A
```

## Notes

The CLI runs Dijkstra to produce the reported distances (matching the C
reference implementation). The BMSSP recursion is exercised with `--verbose`
to print its execution trace.

The C++ implementation uses STL containers (`std::set`, `std::priority_queue`,
`std::unordered_map`) and `std::function` for the DFS subtree size routine.

A hand-written DOT parser is used instead of `std::regex` to avoid known
codegen issues with MinGW's libstdc++.
