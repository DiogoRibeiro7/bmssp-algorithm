# BMSSP - Haskell Implementation

A purely functional Haskell reference implementation of BMSSP from
Duan et al., 2025.

## Build

Using Cabal:

```bash
cabal build
cabal run bmssp -- ../../docs/examples/sample.dot A
```

Or with `runghc` for quick experiments:

```bash
cd app
runghc -i../src Main.hs ../../docs/examples/sample.dot A
```

## Usage

```bash
bmssp [OPTIONS] <graph.dot> <source> [target]
```

Options:
- `--verbose` — print algorithm trace to stderr
- `--json` — emit results as JSON
- `-V`, `--version` — print version
- `-h`, `--help` — show help

## Library API

```haskell
import qualified BMSSP

main :: IO ()
main = do
  let g = foldr (\(u,v,w) acc -> BMSSP.addEdge u v w acc) BMSSP.emptyGraph
            [ ("s", "a", 1)
            , ("s", "b", 4)
            , ("a", "b", 2)
            ]
  print (BMSSP.dijkstra g "s")
```

## Implementation Notes

- Uses `Data.Map.Strict` for distance maps and adjacency, providing
  O(log n) access without mutation.
- Uses `Data.PQueue.Min` (from the `pqueue` package) for the priority queue.
- The CLI reports Dijkstra distances (matching the C reference pattern); the
  BMSSP recursive structure is exercised via `--verbose` for the trace.
- DOT parsing is done with hand-written `String` operations rather than
  Parsec/Megaparsec to keep the dependency footprint minimal.

## Testing

```bash
cabal test
```
