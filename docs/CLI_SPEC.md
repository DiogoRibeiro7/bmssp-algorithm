# CLI Specification

This document defines the standardized command-line interface that every BMSSP implementation must follow. A consistent CLI makes it easy to swap implementations, simplifies the cross-language validation script, and gives users a predictable experience regardless of language.

## Synopsis

```
bmssp [OPTIONS] <graph.dot> <source> [target]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `graph.dot` | yes | Path to a DOT file describing a directed weighted graph. |
| `source` | yes | Name of the source vertex (must exist in the graph). |
| `target` | no | If supplied, only the shortest path from `source` to `target` is printed. |

## Options

| Option | Description |
|--------|-------------|
| `--verbose` | Print algorithm trace to stderr (FindPivots, BMSSP recursion levels, BaseCase calls). |
| `--json` | Emit results as JSON instead of TSV. |
| `--algorithm <name>` | (Optional, future) Switch between `bmssp` (default) and `dijkstra`. |
| `-h`, `--help` | Show usage and exit. |
| `-V`, `--version` | Print version and exit. |

## Output Format

### Default (TSV)

When `target` is omitted, one line per vertex, sorted by vertex name:

```
vertex<TAB>distance
```

- `distance` is a decimal number, or `inf` for unreachable vertices.
- Lines are written to stdout. The trailing newline must be present.

Example for the reference graph (`s->a:1, s->b:4, a->b:2, a->c:5, b->c:1`):

```
a	1
b	3
c	4
s	0
```

When `target` is supplied, output is the path as a single line:

```
s -> a -> b -> c (distance: 4)
```

If the target is unreachable:

```
no path from s to c
```

Exit code is `0` either way (no path is not an error).

### JSON

With `--json`, output is a single JSON object on stdout:

```json
{
  "source": "s",
  "distances": {
    "s": 0,
    "a": 1,
    "b": 3,
    "c": 4
  }
}
```

Unreachable vertices use `null` instead of `inf` to keep the JSON strictly valid.

When `target` is supplied:

```json
{
  "source": "s",
  "target": "c",
  "distance": 4,
  "path": ["s", "a", "b", "c"]
}
```

If unreachable, `distance` is `null` and `path` is `[]`.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (including "no path" when target is unreachable). |
| 1 | Generic error (parse error, source not found, IO error). |
| 2 | Invalid arguments. |

## Error Messages

All errors are written to stderr in the format:

```
bmssp: <message>
```

Examples:

```
bmssp: cannot open graph.dot: no such file or directory
bmssp: source vertex 'x' not found in graph
bmssp: invalid DOT syntax at line 3
```

## Examples

```bash
# All shortest paths from s
bmssp graph.dot s

# Single shortest path
bmssp graph.dot s c

# JSON output
bmssp --json graph.dot s

# With trace
bmssp --verbose graph.dot s
```

## Per-Language Invocation

The binary or entry point name varies, but the arguments after it are identical:

| Language | Invocation |
|----------|------------|
| Go | `./bmssp [OPTIONS] <graph.dot> <source> [target]` |
| C | `./bmssp [OPTIONS] <graph.dot> <source> [target]` |
| Rust | `./bmssp [OPTIONS] <graph.dot> <source> [target]` |
| Java | `java BMSSP [OPTIONS] <graph.dot> <source> [target]` |
| Fortran | `./bmssp [OPTIONS] <graph.dot> <source> [target]` |
| Julia | `julia BMSSPAlgorithm.jl [OPTIONS] <graph.dot> <source> [target]` |

## Conformance

An implementation conforms to this spec if:

1. It accepts the documented arguments and options.
2. It produces byte-identical TSV output for the same input across all conforming implementations (modulo BMSSP's bounded-computation caveat -- see [PARAMETER_SENSITIVITY.md](PARAMETER_SENSITIVITY.md)).
3. It produces semantically identical JSON output (key order may differ).
4. It uses the documented exit codes.

The cross-language validation script (`tests/cross_language_validation.py`) is the source of truth for output format compatibility.
