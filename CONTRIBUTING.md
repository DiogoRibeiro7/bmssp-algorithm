# Contributing

Thanks for your interest in contributing to the BMSSP Algorithm project! This document covers how to get started, run tests, and submit changes.

## Development Setup

Each language has its own prerequisites. Install only what you need:

| Language | Prerequisites |
|----------|--------------|
| Go | Go 1.21+ |
| C | GCC or Clang, Make, Python 3 + pytest |
| Rust | Rust toolchain (rustup), clippy, rustfmt |
| Java | JDK 17+ |
| Fortran | gfortran, Make, Python 3 + pytest |
| Julia | Julia 1.9+ |

Clone the repo and navigate to the implementation you want to work on:

```bash
git clone https://github.com/DiogoRibeiro7/bmssp-algorithm.git
cd bmssp-algorithm/implementations/<language>
```

## Running Tests

```bash
# Go
cd implementations/go && go test -v -race ./...

# C
cd implementations/c && make test

# Rust
cd implementations/rust && cargo test

# Java
cd implementations/java && javac BMSSP.java BMSSPTest.java && java BMSSPTest

# Fortran
cd implementations/fortran && make test

# Julia
cd implementations/julia && julia tests/test_bmssp.jl

# Cross-language validation (requires all toolchains)
python tests/cross_language_validation.py
```

## Submitting Changes

1. Fork the repository and create a feature branch from `main`.
2. Make your changes, following the guidelines below.
3. Run the relevant tests locally.
4. Open a pull request against `main`.
5. CI must pass and at least one review is required before merging.

## Coding Standards

- **Algorithmic fidelity** -- preserve the theoretical structure from the paper. Do not simplify the algorithm in ways that change its complexity class.
- **Paper notation** -- use variable names consistent with the research paper (e.g. `d_hat`, `B`, `S`, `U`, `k`, `t`, `l`).
- **Test coverage** -- add tests for any new functionality. Test BMSSP-specific behavior (bounded computation, pivot selection), not just standard SSSP correctness.
- **Documentation** -- explain implementation-specific choices or deviations from the paper.

## Adding a New Language

1. Create `implementations/<language>/` with the main source file, a `README.md`, and a `tests/` directory.
2. Implement all core components: `Graph`, `DQueue`, `FindPivots`, `BaseCase`, `BMSSP`, `RunSSSP`.
3. Add tests covering at least: basic SSSP, single vertex, disconnected graph, and DQueue operations.
4. Add a CI job in `.github/workflows/ci.yml`.
5. Update the root `README.md` implementation table.
6. Open a PR using the "New Language Implementation" issue template.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). Breaking changes to the public API of any implementation bump the major version.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold these standards.

## Questions

For algorithm questions, refer to the [original paper](https://arxiv.org/abs/2504.17033). For project questions, use [GitHub Discussions](https://github.com/DiogoRibeiro7/bmssp-algorithm/discussions).
