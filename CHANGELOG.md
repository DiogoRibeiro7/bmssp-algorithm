# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Rust test suite (15 tests covering SSSP, DQueue, and Graph edge cases)
- Java test suite (BMSSPTest.java with 51 assertions)
- Cross-language correctness validation script
- GitHub Actions CI for all 6 languages with code coverage (Go, Rust)
- Benchmark workflow with artifact upload
- Dependabot for Go, Rust, GitHub Actions, and Python dependencies
- Issue templates: bug report, feature request, new language, general
- Pull request template
- Stale issue/PR bot
- Branch protection on main
- GitHub Discussions enabled
- Makefiles for C and Fortran implementations
- CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, CITATION.cff
- ROADMAP.md with phased development plan
- MIT License
- golangci-lint, rustfmt, and JuliaFormatter checks in CI

### Changed

- Rewritten README with badges, implementation table, and quick start guides
- Repository renamed from `bmssp_private` to `bmssp-algorithm`
- Rust `run_sssp` now routes through full `bmssp()` algorithm
- Resolved Rust compiler warnings (unused mut, dead code)

## [0.1.0] - 2025-01-01

### Added

- Initial implementations in Go, C, Rust, Java, Fortran
- Julia implementation
- Test suites for Go, C, Fortran, Julia
- Benchmark suite (performance_comparison.py)
- Visualization tools (recursion trees, frontier evolution)
- Algorithm walkthrough and parameter sensitivity documentation
- DOT file parser in C implementation
