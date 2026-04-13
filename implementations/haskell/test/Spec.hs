module Main where

import qualified BMSSP
import qualified Data.Map.Strict as Map
import System.Exit (exitFailure, exitSuccess)

main :: IO ()
main = do
  let tests =
        [ ("dijkstra basic", testDijkstraBasic)
        , ("zero weight edges", testZeroWeights)
        , ("linear path", testLinearPath)
        , ("disconnected nodes", testDisconnected)
        ]
  results <- mapM runTest tests
  if all id results
    then do
      putStrLn $ "All " ++ show (length tests) ++ " tests passed."
      exitSuccess
    else exitFailure
  where
    runTest (name, action) = do
      ok <- action
      putStrLn $ (if ok then "[PASS] " else "[FAIL] ") ++ name
      return ok

testDijkstraBasic :: IO Bool
testDijkstraBasic = do
  let g = foldr (\(u, v, w) acc -> BMSSP.addEdge u v w acc) BMSSP.emptyGraph
            [ ("s", "a", 1)
            , ("s", "b", 4)
            , ("a", "b", 2)
            , ("a", "c", 5)
            , ("b", "c", 1)
            ]
      d = BMSSP.drDist (BMSSP.dijkstra g "s")
  return $ Map.lookup "s" d == Just 0
        && Map.lookup "a" d == Just 1
        && Map.lookup "b" d == Just 3
        && Map.lookup "c" d == Just 4

testZeroWeights :: IO Bool
testZeroWeights = do
  let g = foldr (\(u, v, w) acc -> BMSSP.addEdge u v w acc) BMSSP.emptyGraph
            [("s", "a", 0), ("a", "b", 0)]
      d = BMSSP.drDist (BMSSP.dijkstra g "s")
  return $ Map.lookup "s" d == Just 0
        && Map.lookup "a" d == Just 0
        && Map.lookup "b" d == Just 0

testLinearPath :: IO Bool
testLinearPath = do
  let g = foldr (\(u, v, w) acc -> BMSSP.addEdge u v w acc) BMSSP.emptyGraph
            [("a", "b", 1), ("b", "c", 2), ("c", "d", 3)]
      d = BMSSP.drDist (BMSSP.dijkstra g "a")
  return $ Map.lookup "a" d == Just 0
        && Map.lookup "b" d == Just 1
        && Map.lookup "c" d == Just 3
        && Map.lookup "d" d == Just 6

testDisconnected :: IO Bool
testDisconnected = do
  -- s -> a, b -> c (b and c unreachable from s)
  let g = foldr (\(u, v, w) acc -> BMSSP.addEdge u v w acc) BMSSP.emptyGraph
            [("s", "a", 1), ("b", "c", 2)]
      d = BMSSP.drDist (BMSSP.dijkstra g "s")
  return $ Map.lookup "s" d == Just 0
        && Map.lookup "a" d == Just 1
        && case Map.lookup "b" d of
             Just x  -> isInfinite x
             _ -> False
        && case Map.lookup "c" d of
             Just x  -> isInfinite x
             _ -> False
