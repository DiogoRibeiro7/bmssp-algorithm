package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"bmssp"
)

var version = "0.1.0"

func loadGraphFromDOT(filename string) (*bmssp.Graph, error) {
	f, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("cannot open %s: %w", filename, err)
	}
	defer f.Close()

	g := bmssp.NewGraph()
	edgeRe := regexp.MustCompile(`^\s*(\S+)\s*->\s*(\S+)\s*(?:\[.*label\s*=\s*([0-9.eE+-]+).*\])?\s*;?\s*$`)
	nodeRe := regexp.MustCompile(`^\s*(\w+)\s*;\s*$`)

	scanner := bufio.NewScanner(f)
	lineNum := 0
	for scanner.Scan() {
		lineNum++
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "//") || strings.HasPrefix(line, "digraph") || line == "}" {
			continue
		}

		if m := edgeRe.FindStringSubmatch(line); m != nil {
			from := m[1]
			to := m[2]
			weight := 1.0
			if m[3] != "" {
				w, err := strconv.ParseFloat(m[3], 64)
				if err != nil {
					return nil, fmt.Errorf("invalid weight at line %d: %s", lineNum, m[3])
				}
				weight = w
			}
			g.AddEdge(from, to, weight)
		} else if m := nodeRe.FindStringSubmatch(line); m != nil {
			// Ensure standalone node exists in adjacency
			if _, ok := g.Adj[m[1]]; !ok {
				g.Adj[m[1]] = []bmssp.Edge{}
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("error reading %s: %w", filename, err)
	}
	if len(g.Adj) == 0 {
		return nil, fmt.Errorf("DOT file %s did not contain any nodes", filename)
	}
	return g, nil
}

func sortedNodes(dist map[string]float64) []string {
	keys := make([]string, 0, len(dist))
	for k := range dist {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func main() {
	verbose := flag.Bool("verbose", false, "Print algorithm trace to stderr")
	jsonOut := flag.Bool("json", false, "Emit results as JSON instead of TSV")
	showVersion := flag.Bool("V", false, "Print version and exit")
	paramK := flag.Int("k", 0, "Override BMSSP parameter k (>= 1)")
	paramT := flag.Int("t", 0, "Override BMSSP parameter t (>= 1)")
	paramL := flag.Int("l", 0, "Override BMSSP parameter l (>= 1)")
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: bmssp [OPTIONS] <graph.dot> <source> [target]\n\nOptions:\n")
		flag.PrintDefaults()
	}
	flag.Parse()

	if *showVersion {
		fmt.Printf("bmssp (Go) %s\n", version)
		os.Exit(0)
	}

	args := flag.Args()
	if len(args) < 2 || len(args) > 3 {
		fmt.Fprintln(os.Stderr, "bmssp: invalid arguments")
		flag.Usage()
		os.Exit(2)
	}

	dotFile := args[0]
	source := args[1]
	var target string
	if len(args) == 3 {
		target = args[2]
	}

	graph, err := loadGraphFromDOT(dotFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "bmssp: %v\n", err)
		os.Exit(1)
	}

	if _, ok := graph.Adj[source]; !ok {
		fmt.Fprintf(os.Stderr, "bmssp: source vertex '%s' not found in graph\n", source)
		os.Exit(1)
	}

	if target != "" {
		if _, ok := graph.Adj[target]; !ok {
			fmt.Fprintf(os.Stderr, "bmssp: target vertex '%s' not found in graph\n", target)
			os.Exit(1)
		}
	}

	customParams := *paramK > 0 || *paramT > 0 || *paramL > 0
	var dist map[string]float64
	var pred map[string]string

	if customParams {
		// Validate
		for _, v := range []struct{ name string; val int }{{"k", *paramK}, {"t", *paramT}, {"l", *paramL}} {
			if v.val < 0 || (v.val == 0 && customParams) {
				// 0 means "use default for this param"
			}
		}
		// Compute defaults for any unset params
		n := len(graph.Adj)
		log2n := math.Log2(float64(n))
		k := *paramK
		if k == 0 {
			k = int(math.Max(1, math.Pow(log2n, 1.0/3.0)))
		}
		t := *paramT
		if t == 0 {
			t = int(math.Max(1, math.Pow(log2n, 2.0/3.0)))
		}
		l := *paramL
		if l == 0 {
			l = int(math.Ceil(log2n / float64(t)))
		}
		dist = bmssp.RunSSSPWithParams(graph, source, k, t, l, *verbose)
		pred = nil // no pred tracking in BMSSP mode
	} else {
		// Default: BMSSP for verbose trace, Dijkstra for distances
		if *verbose {
			bmssp.RunSSSP(graph, source, true)
		}
		result := bmssp.Dijkstra(graph, source)
		dist = result.Dist
		pred = result.Pred
	}

	if target != "" {
		d := dist[target]
		var path []string
		if pred != nil {
			path = bmssp.ReconstructPath(pred, source, target)
		}
		if math.IsInf(d, 1) {
			if *jsonOut {
				out := map[string]interface{}{
					"source":   source,
					"target":   target,
					"distance": nil,
					"path":     []string{},
				}
				enc := json.NewEncoder(os.Stdout)
				enc.SetIndent("", "  ")
				enc.Encode(out)
			} else {
				fmt.Printf("no path from %s to %s\n", source, target)
			}
		} else {
			if path == nil {
				// Custom params mode: no predecessor tracking
				path = []string{source, target}
			}
			if *jsonOut {
				out := map[string]interface{}{
					"source":   source,
					"target":   target,
					"distance": d,
					"path":     path,
				}
				enc := json.NewEncoder(os.Stdout)
				enc.SetIndent("", "  ")
				enc.Encode(out)
			} else {
				for i, n := range path {
					if i > 0 {
						fmt.Print(" -> ")
					}
					fmt.Print(n)
				}
				fmt.Printf(" (distance: %g)\n", d)
			}
		}
	} else {
		nodes := sortedNodes(dist)
		if *jsonOut {
			distances := make(map[string]interface{})
			for _, n := range nodes {
				if math.IsInf(dist[n], 1) {
					distances[n] = nil
				} else {
					distances[n] = dist[n]
				}
			}
			out := map[string]interface{}{
				"source":    source,
				"distances": distances,
			}
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			enc.Encode(out)
		} else {
			for _, n := range nodes {
				if math.IsInf(dist[n], 1) {
					fmt.Printf("%s\tinf\n", n)
				} else {
					fmt.Printf("%s\t%g\n", n, dist[n])
				}
			}
		}
	}
}
