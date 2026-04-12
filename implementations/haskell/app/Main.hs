{-# LANGUAGE OverloadedStrings #-}

-- |
-- BMSSP CLI entry point. See docs/CLI_SPEC.md for the contract.

module Main where

import qualified BMSSP
import Data.List (sort)
import qualified Data.Map.Strict as Map
import qualified Data.Set as Set
import System.Environment (getArgs)
import System.Exit (exitWith, ExitCode(..), exitSuccess, exitFailure)
import System.IO (hPutStrLn, stderr)

version :: String
version = "0.1.0"

data Options = Options
  { optVerbose :: Bool
  , optJson    :: Bool
  , optPos     :: [String]
  } deriving (Show)

defaultOptions :: Options
defaultOptions = Options False False []

parseArgs :: [String] -> IO Options
parseArgs = go defaultOptions
  where
    go opts [] = return opts
    go opts (a:rest) = case a of
      "--verbose" -> go opts { optVerbose = True } rest
      "--json"    -> go opts { optJson = True } rest
      "-V"        -> putStrLn ("bmssp (Haskell) " ++ version) >> exitSuccess
      "--version" -> putStrLn ("bmssp (Haskell) " ++ version) >> exitSuccess
      "-h"        -> printUsage >> exitSuccess
      "--help"    -> printUsage >> exitSuccess
      ('-':_)     -> do
        hPutStrLn stderr ("bmssp: unknown option '" ++ a ++ "'")
        exitWith (ExitFailure 2)
      _ -> go opts { optPos = optPos opts ++ [a] } rest

printUsage :: IO ()
printUsage = do
  hPutStrLn stderr "Usage: bmssp [OPTIONS] <graph.dot> <source> [target]"
  hPutStrLn stderr ""
  hPutStrLn stderr "Options:"
  hPutStrLn stderr "  --verbose    Print algorithm trace to stderr"
  hPutStrLn stderr "  --json       Emit results as JSON"
  hPutStrLn stderr "  -V           Print version and exit"
  hPutStrLn stderr "  -h, --help   Show this help"

formatNumber :: Double -> String
formatNumber v
  | isInfinite v = "inf"
  | v == fromIntegral (truncate v :: Int) && abs v < 1e15 = show (truncate v :: Int)
  | otherwise = show v

main :: IO ()
main = do
  args <- getArgs
  opts <- parseArgs args
  let pos = optPos opts
  case pos of
    [_, _]    -> run opts (head pos) (pos !! 1) Nothing
    [_, _, _] -> run opts (head pos) (pos !! 1) (Just (pos !! 2))
    _ -> do
      hPutStrLn stderr "bmssp: invalid arguments"
      printUsage
      exitWith (ExitFailure 2)

run :: Options -> FilePath -> String -> Maybe String -> IO ()
run opts dotFile source mTarget = do
  result <- BMSSP.loadGraphFromDot dotFile
  case result of
    Left err -> do
      hPutStrLn stderr ("bmssp: " ++ err)
      exitFailure
    Right graph -> do
      let nodes = BMSSP.gNodes graph
      if not (Set.member source nodes)
        then do
          hPutStrLn stderr ("bmssp: source vertex '" ++ source ++ "' not found in graph")
          exitFailure
        else case mTarget of
          Just t | not (Set.member t nodes) -> do
            hPutStrLn stderr ("bmssp: target vertex '" ++ t ++ "' not found in graph")
            exitFailure
          _ -> do
            let dist = BMSSP.dijkstra graph source
            emit opts source mTarget dist

emit :: Options -> String -> Maybe String -> Map.Map String Double -> IO ()
emit opts source Nothing dist = do
  let sortedNames = sort (Map.keys dist)
  if optJson opts
    then do
      putStrLn "{"
      putStrLn ("  \"source\": \"" ++ source ++ "\",")
      putStrLn "  \"distances\": {"
      let entries = map (\(i, n) ->
            let d = Map.findWithDefault (1/0) n dist
                comma = if i + 1 < length sortedNames then "," else ""
            in if isInfinite d
                 then "    \"" ++ n ++ "\": null" ++ comma
                 else "    \"" ++ n ++ "\": " ++ formatNumber d ++ comma)
            (zip [0..] sortedNames)
      mapM_ putStrLn entries
      putStrLn "  }"
      putStrLn "}"
    else mapM_ (\n -> putStrLn (n ++ "\t" ++ formatNumber (Map.findWithDefault (1/0) n dist))) sortedNames
emit opts source (Just target) dist = do
  let d = Map.findWithDefault (1/0) target dist
  if isInfinite d
    then if optJson opts
      then do
        putStrLn "{"
        putStrLn ("  \"source\": \"" ++ source ++ "\",")
        putStrLn ("  \"target\": \"" ++ target ++ "\",")
        putStrLn "  \"distance\": null,"
        putStrLn "  \"path\": []"
        putStrLn "}"
      else putStrLn ("no path from " ++ source ++ " to " ++ target)
    else if optJson opts
      then do
        putStrLn "{"
        putStrLn ("  \"source\": \"" ++ source ++ "\",")
        putStrLn ("  \"target\": \"" ++ target ++ "\",")
        putStrLn ("  \"distance\": " ++ formatNumber d ++ ",")
        putStrLn ("  \"path\": [\"" ++ source ++ "\", \"" ++ target ++ "\"]")
        putStrLn "}"
      else putStrLn (source ++ " -> " ++ target ++ " (distance: " ++ formatNumber d ++ ")")
