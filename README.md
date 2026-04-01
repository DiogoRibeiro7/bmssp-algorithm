<div align="center">

# BMSSP Algorithm

**Multi-language reference implementations of the first deterministic algorithm to break Dijkstra's sorting barrier for directed single-source shortest paths.**

[![CI](https://github.com/DiogoRibeiro7/bmssp-algorithm/actions/workflows/ci.yml/badge.svg)](https://github.com/DiogoRibeiro7/bmssp-algorithm/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go&logoColor=white)](#go)
[![Rust](https://img.shields.io/badge/Rust-1.70+-DEA584?logo=rust&logoColor=white)](#rust)
[![C](https://img.shields.io/badge/C-C11-A8B9CC?logo=c&logoColor=white)](#c)
[![Java](https://img.shields.io/badge/Java-17+-ED8B00?logo=openjdk&logoColor=white)](#java)
[![Fortran](https://img.shields.io/badge/Fortran-2008-734F96)](#fortran)
[![Julia](https://img.shields.io/badge/Julia-1.9+-9558B2?logo=julia&logoColor=white)](#julia)

[Paper](https://arxiv.org/abs/2504.17033) | [Algorithm Walkthrough](docs/bmssp-walkthrough.md) | [Benchmarks](benchmarks/README.md) | [Visualization](vizualization/README.md)

</div>

---

## Overview

This repository implements the algorithms from:

> **Breaking the Sorting Barrier for Directed Single-Source Shortest Paths**
> Ran Duan, Jiayi Mao, Xiao Mao, Xinkai Shu, Longhui Yin (2025)
> [arXiv:2504.17033v2](https://arxiv.org/abs/2504.17033)

The BMSSP algorithm achieves **O(m log<sup>2/3</sup> n)** deterministic time for directed SSSP in the comparison-addition model, breaking Dijkstra's long-standing **O(m + n log n)** barrier. It proves that while Dijkstra's approach is optimal when vertex ordering is required, it is not optimal for computing distances alone.

> **Note**: These are research implementations optimized for algorithmic clarity, not production use. For practical shortest-path computation, use standard Dijkstra or A* implementations.

## How It Works

BMSSP combines ideas from Dijkstra's algorithm and Bellman-Ford through a recursive partitioning strategy:

| Component | Role | Reference |
|-----------|------|-----------|
| **FindPivots** | Bounded Bellman-Ford expansion to identify pivot vertices covering large subtrees | Lemma 3.2 |
| **BaseCase** | Small-instance solver using a Dijkstra-like approach | Section 3 |
| **BMSSP** | Main recursive bounded multi-source shortest path solver | Algorithm 3 |
| **DQueue** | Specialized queue supporting bounded batch pull and prepend operations | Lemma 3.3 |

**Key parameters** (derived from graph size _n_):

- `k = floor(log^(1/3) n)` -- controls pivot selection and base case size
- `t = floor(log^(2/3) n)` -- recursion branching factor
- `l = ceil(log n / t)` -- number of recursion levels

See the [algorithm walkthrough](docs/bmssp-walkthrough.md) and [parameter sensitivity analysis](docs/PARAMETER_SENSITIVITY.md) for details.

## Implementations

| Language | Source | Tests | Build |
|----------|--------|-------|-------|
| **Go** | [bmssp.go](implementations/go/bmssp.go) | `go test ./...` | `go run bmssp.go` |
| **C** | [bmssp.c](implementations/c/bmssp.c) | `python -m pytest tests/` | `gcc bmssp.c -lm -o bmssp` |
| **Rust** | [main.rs](implementations/rust/src/main.rs) | `cargo test` | `cargo run` |
| **Java** | [BMSSP.java](implementations/java/BMSSP.java) | `javac BMSSPTest.java && java BMSSPTest` | `javac BMSSP.java && java BMSSP` |
| **Fortran** | [bmssp.f90](implementations/fortran/bmssp.f90) | `python -m pytest tests/` | `gfortran bmssp.f90 -o bmssp` |
| **Julia** | [BMSSPAlgorithm.jl](implementations/julia/BMSSPAlgorithm/src/BMSSPAlgorithm.jl) | `julia tests/test_bmssp.jl` | `julia src/BMSSPAlgorithm.jl` |

Each implementation lives under `implementations/<language>/` with its own README, source, and test directory.

## Quick Start

### Go

```bash
cd implementations/go
go run bmssp.go
go test ./...
```

### C

The C implementation accepts [DOT files](docs/examples/README.md) from the command line:

```bash
cd implementations/c
gcc bmssp.c -lm -o bmssp
./bmssp ../docs/examples/sample.dot A       # all shortest paths from A
./bmssp ../docs/examples/sample.dot A H     # shortest path from A to H
```

### Rust

```bash
cd implementations/rust
cargo run
cargo test
```

### Java

```bash
cd implementations/java
javac BMSSP.java
java BMSSP
```

### Fortran

```bash
cd implementations/fortran
gfortran bmssp.f90 -o bmssp
./bmssp
```

### Julia

```bash
cd implementations/julia
julia BMSSPAlgorithm/src/BMSSPAlgorithm.jl
julia tests/test_bmssp.jl
```

## Benchmarks

The benchmark suite compares BMSSP against Dijkstra across different graph topologies and sizes.

```bash
cd benchmarks
pip install -r requirements.txt
python performance_comparison.py
```

| Graph Type | Crossover Point | Max Improvement | Memory Reduction |
|------------|----------------|-----------------|------------------|
| Sparse Random | n ~ 200--500 | ~60% faster | ~20% |
| Scale-Free | n ~ 100--300 | ~70% faster | ~25% |
| Small-World | n ~ 300--600 | ~50% faster | ~15% |
| Grid | n ~ 400--800 | ~40% faster | ~10% |

See [benchmarks/README.md](benchmarks/README.md) for methodology and interpretation.

## Visualization

Interactive and static visualizations of recursion trees, frontier evolution, and pivot selection:

```bash
cd vizualization
pip install -r requirements.txt
python bmssp_visualization.py
```

See [vizualization/README.md](vizualization/README.md) for all available tools and scripts.

## Repository Structure

```
bmssp-algorithm/
├── implementations/
│   ├── go/            # Go implementation + tests
│   ├── c/             # C implementation with DOT parser + tests
│   ├── rust/          # Rust implementation
│   ├── java/          # Java implementation
│   ├── fortran/       # Fortran implementation + tests
│   └── julia/         # Julia implementation + tests
├── docs/
│   ├── bmssp-walkthrough.md        # Step-by-step algorithm guide
│   ├── PARAMETER_SENSITIVITY.md    # Parameter analysis
│   └── examples/                   # DOT file examples
├── benchmarks/                     # Performance comparison suite
├── vizualization/                  # Visualization tools
├── paper/                          # Reference paper
└── .github/
    ├── workflows/                  # CI/CD pipelines
    ├── ISSUE_TEMPLATE/             # Issue templates
    └── dependabot.yml              # Dependency updates
```

## Technical Details

**Time complexity**: O(m log<sup>2/3</sup> n) deterministic, in the comparison-addition model with real non-negative edge weights.

**Graph preprocessing**: All implementations assume constant-degree graphs. For general graphs, a standard vertex-splitting transformation achieves constant in/out-degree while preserving shortest paths.

**Limitations**:
- May not compute complete shortest-path trees due to bounded termination conditions
- Parameter-sensitive: uses theoretically-derived values of _k_ and _t_
- Outperforms Dijkstra only beyond a crossover point (typically n > 100--500)

## Citation

```bibtex
@article{duan2025breaking,
  title   = {Breaking the Sorting Barrier for Directed Single-Source Shortest Paths},
  author  = {Duan, Ran and Mao, Jiayi and Mao, Xiao and Shu, Xinkai and Yin, Longhui},
  journal = {arXiv preprint arXiv:2504.17033},
  year    = {2025}
}
```

## Contributing

1. **Algorithmic fidelity** -- preserve the theoretical structure from the paper
2. **Paper notation** -- use variable names consistent with the research
3. **Test coverage** -- validate BMSSP-specific behavior, not just standard SSSP
4. **Documentation** -- explain implementation-specific choices

See [issue templates](.github/ISSUE_TEMPLATE/) for bug reports, feature requests, and new language proposals.

## License

This project is licensed under the [MIT License](LICENSE).
