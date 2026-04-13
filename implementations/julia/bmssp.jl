#!/usr/bin/env julia

# Activate the local project so BMSSPAlgorithm is available
using Pkg
Pkg.activate(joinpath(@__DIR__, "BMSSPAlgorithm"); io=devnull)

using BMSSPAlgorithm
import BMSSPAlgorithm: Graph, add_edge!, run_sssp, dijkstra, reconstruct_path, load_graph_from_dot
using JSON

const VERSION = "0.1.0"

function format_number(v::Float64)
    if v == floor(v) && abs(v) < 1e15
        return string(Int(v))
    end
    return string(v)
end

function main()
    verbose = false
    json_out = false
    positional = String[]

    i = 1
    while i <= length(ARGS)
        arg = ARGS[i]
        if arg == "--verbose"
            verbose = true
        elseif arg == "--json"
            json_out = true
        elseif arg in ("-V", "--version")
            println("bmssp (Julia) $VERSION")
            exit(0)
        elseif arg in ("-h", "--help")
            println(stderr, "Usage: julia bmssp.jl [OPTIONS] <graph.dot> <source> [target]")
            exit(0)
        elseif startswith(arg, "-")
            println(stderr, "bmssp: unknown option '$arg'")
            exit(2)
        else
            push!(positional, arg)
        end
        i += 1
    end

    if length(positional) < 2 || length(positional) > 3
        println(stderr, "bmssp: invalid arguments")
        println(stderr, "Usage: julia bmssp.jl [OPTIONS] <graph.dot> <source> [target]")
        exit(2)
    end

    dot_file = positional[1]
    source = positional[2]
    target = length(positional) == 3 ? positional[3] : nothing

    local graph::Graph
    try
        graph = load_graph_from_dot(dot_file)
    catch e
        println(stderr, "bmssp: $e")
        exit(1)
    end

    if !haskey(graph.adj, source)
        println(stderr, "bmssp: source vertex '$source' not found in graph")
        exit(1)
    end

    if target !== nothing && !haskey(graph.adj, target)
        println(stderr, "bmssp: target vertex '$target' not found in graph")
        exit(1)
    end

    dist, pred = dijkstra(graph, source)
    sorted_nodes = sort(collect(keys(dist)))

    if target !== nothing
        d = get(dist, target, Inf)
        path = reconstruct_path(pred, source, target)
        if isinf(d) || path === nothing
            if json_out
                result = Dict("source" => source, "target" => target,
                              "distance" => nothing, "path" => String[])
                println(JSON.json(result, 2))
            else
                println("no path from $source to $target")
            end
        else
            if json_out
                result = Dict("source" => source, "target" => target,
                              "distance" => d == floor(d) ? Int(d) : d,
                              "path" => path)
                println(JSON.json(result, 2))
            else
                println("$(join(path, " -> ")) (distance: $(format_number(d)))")
            end
        end
    elseif json_out
        distances = Dict{String, Any}()
        for n in sorted_nodes
            distances[n] = isinf(dist[n]) ? nothing : (dist[n] == floor(dist[n]) ? Int(dist[n]) : dist[n])
        end
        result = Dict("source" => source, "distances" => distances)
        println(JSON.json(result, 2))
    else
        for n in sorted_nodes
            if isinf(dist[n])
                println("$n\tinf")
            else
                println("$n\t$(format_number(dist[n]))")
            end
        end
    end
end

main()
