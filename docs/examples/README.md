# Example DOT Graphs

This directory contains small DOT files that can be fed directly to the command-line utilities in `implementations/`.

## `sample.dot`

A weighted directed graph illustrating the example from the project README. Use it to exercise the C CLI:

```bash
cd implementations/c
gcc bmssp.c -lm -o bmssp
./bmssp ../../docs/examples/sample.dot A
```

Pass a target vertex as a third argument to print a single path:

```bash
./bmssp ../../docs/examples/sample.dot A H
```
