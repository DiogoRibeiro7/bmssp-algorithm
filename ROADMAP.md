# Roadmap

This document outlines the planned development direction for the BMSSP Algorithm project.

## Phase 1 -- Foundation (Current)

- [x] Core implementations in Go, C, Rust, Java, Fortran, Julia
- [x] Basic test suites for Go, C, Fortran, Julia
- [x] Benchmark suite comparing BMSSP vs Dijkstra
- [x] Visualization tools for recursion trees and frontier evolution
- [x] Algorithm walkthrough and parameter sensitivity documentation
- [x] DOT file parser in C implementation
- [x] CI pipeline for all languages
- [x] Issue templates and Dependabot configuration

## Phase 2 -- Test Coverage and Correctness

- [x] Add automated tests for Rust implementation
- [x] Add automated tests for Java implementation
- [x] Cross-language correctness validation (same input graphs produce identical distances)
- [x] Property-based testing for DQueue invariants
- [x] Edge-case test suite (single vertex, self-loops, zero-weight edges, large fan-out)
- [x] Code coverage reporting in CI

## Phase 3 -- Usability and Tooling

- [x] DOT file input support for all implementations (not just C)
- [x] Unified CLI interface across languages
- [x] Docker images for each implementation
- [x] Pre-built binaries via GitHub Releases
- [x] Interactive web demo for small graphs
- [x] Add a LICENSE file (MIT)

## Phase 4 -- Performance and Analysis

- [x] Automated performance regression detection in CI
- [x] Benchmark results tracked over time with historical comparison
- [x] Memory profiling for each implementation
- [x] Comparison against other advanced SSSP algorithms (Thorup, Pettie-Ramachandran)
- [x] Large-graph benchmarks (n > 10^6)
- [x] Platform-specific optimization notes (SIMD, cache behavior)

## Phase 5 -- Community and Research

- [x] C++ implementation
- [ ] ~~Python implementation~~ (removed — not needed)
- [x] Haskell or OCaml implementation (functional perspective)
- [x] Integration examples with popular graph libraries (NetworkX, JGraphT, petgraph)
- [x] Tutorial series: "Understanding BMSSP step by step"
- [x] Comparison write-up: when to use BMSSP vs Dijkstra in practice

## Non-Goals

- Production-grade shortest-path library (this is a research reference)
- GPU or distributed implementations (out of scope for the comparison-addition model)
- Support for negative edge weights (the algorithm assumes non-negative weights)

---

Contributions toward any of these items are welcome. Open an issue to discuss before starting large changes.
