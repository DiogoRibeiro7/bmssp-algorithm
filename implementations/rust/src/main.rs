use bmssp::{dijkstra, reconstruct_path, run_sssp, Graph};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::process;

const VERSION: &str = "0.1.0";

fn load_graph_from_dot(filename: &str) -> Result<Graph, String> {
    let content = fs::read_to_string(filename)
        .map_err(|e| format!("cannot open {}: {}", filename, e))?;

    let mut g = Graph::new();
    let edge_re = regex_lite::Regex::new(
        r"^\s*(\S+)\s*->\s*(\S+)\s*(?:\[.*label\s*=\s*([0-9.eE+-]+).*\])?\s*;?\s*$",
    )
    .unwrap();
    let node_re = regex_lite::Regex::new(r"^\s*(\w+)\s*;\s*$").unwrap();

    for (i, line) in content.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty()
            || trimmed.starts_with("//")
            || trimmed.starts_with("digraph")
            || trimmed == "}"
        {
            continue;
        }

        if let Some(caps) = edge_re.captures(trimmed) {
            let from = caps.get(1).unwrap().as_str();
            let to = caps.get(2).unwrap().as_str();
            let weight: f64 = match caps.get(3) {
                Some(m) => m.as_str().parse().map_err(|_| {
                    format!("invalid weight at line {}: {}", i + 1, m.as_str())
                })?,
                None => 1.0,
            };
            g.add_edge(from, to, weight);
        } else if let Some(caps) = node_re.captures(trimmed) {
            let node = caps.get(1).unwrap().as_str();
            g.adj.entry(node.to_string()).or_default();
        }
    }

    if g.adj.is_empty() {
        return Err(format!("DOT file {} did not contain any nodes", filename));
    }
    Ok(g)
}

fn print_usage() {
    eprintln!("Usage: bmssp [OPTIONS] <graph.dot> <source> [target]");
    eprintln!();
    eprintln!("Options:");
    eprintln!("  --verbose    Print algorithm trace to stderr");
    eprintln!("  --json       Emit results as JSON instead of TSV");
    eprintln!("  -V           Print version and exit");
    eprintln!("  -h, --help   Show this help");
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();

    let mut verbose = false;
    let mut json_out = false;
    let mut positional = Vec::new();

    for arg in &args {
        match arg.as_str() {
            "--verbose" => verbose = true,
            "--json" => json_out = true,
            "-V" | "--version" => {
                println!("bmssp (Rust) {}", VERSION);
                process::exit(0);
            }
            "-h" | "--help" => {
                print_usage();
                process::exit(0);
            }
            _ if arg.starts_with('-') => {
                eprintln!("bmssp: unknown option '{}'", arg);
                print_usage();
                process::exit(2);
            }
            _ => positional.push(arg.as_str()),
        }
    }

    if positional.len() < 2 || positional.len() > 3 {
        eprintln!("bmssp: invalid arguments");
        print_usage();
        process::exit(2);
    }

    let dot_file = positional[0];
    let source = positional[1];
    let target = positional.get(2).copied();

    let graph = match load_graph_from_dot(dot_file) {
        Ok(g) => g,
        Err(e) => {
            eprintln!("bmssp: {}", e);
            process::exit(1);
        }
    };

    if !graph.adj.contains_key(source) {
        eprintln!("bmssp: source vertex '{}' not found in graph", source);
        process::exit(1);
    }

    if let Some(t) = target {
        if !graph.adj.contains_key(t) {
            eprintln!("bmssp: target vertex '{}' not found in graph", t);
            process::exit(1);
        }
    }

    // Run BMSSP for the verbose trace, then Dijkstra for the actual distances
    // (matches the C reference implementation pattern).
    if verbose {
        run_sssp(&graph, source, true);
    }
    let result = dijkstra(&graph, source);
    let dist = &result.dist;
    let pred = &result.pred;

    // Sort by node name for deterministic output
    let sorted: BTreeMap<&String, &f64> = dist.iter().collect();

    if let Some(t) = target {
        let d = dist.get(t).copied().unwrap_or(f64::INFINITY);
        let path = reconstruct_path(pred, source, t);
        if d.is_infinite() || path.is_none() {
            if json_out {
                println!(
                    "{{\n  \"source\": \"{}\",\n  \"target\": \"{}\",\n  \"distance\": null,\n  \"path\": []\n}}",
                    source, t
                );
            } else {
                println!("no path from {} to {}", source, t);
            }
        } else {
            let path = path.unwrap();
            if json_out {
                let path_json: Vec<String> = path.iter().map(|p| format!("\"{}\"", p)).collect();
                println!(
                    "{{\n  \"source\": \"{}\",\n  \"target\": \"{}\",\n  \"distance\": {},\n  \"path\": [{}]\n}}",
                    source, t, format_number(d), path_json.join(", ")
                );
            } else {
                println!("{} (distance: {})", path.join(" -> "), format_number(d));
            }
        }
    } else if json_out {
        println!("{{");
        println!("  \"source\": \"{}\",", source);
        println!("  \"distances\": {{");
        let entries: Vec<_> = sorted.iter().collect();
        for (i, (node, dist)) in entries.iter().enumerate() {
            let comma = if i + 1 < entries.len() { "," } else { "" };
            if dist.is_infinite() {
                println!("    \"{}\": null{}", node, comma);
            } else {
                println!("    \"{}\": {}{}", node, format_number(***dist), comma);
            }
        }
        println!("  }}");
        println!("}}");
    } else {
        for (node, d) in &sorted {
            if d.is_infinite() {
                println!("{}\tinf", node);
            } else {
                println!("{}\t{}", node, format_number(**d));
            }
        }
    }
}

fn format_number(v: f64) -> String {
    if v == v.floor() && v.abs() < 1e15 {
        format!("{}", v as i64)
    } else {
        format!("{}", v)
    }
}
