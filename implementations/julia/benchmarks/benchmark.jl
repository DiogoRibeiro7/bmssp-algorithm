#!/usr/bin/env julia
"""
benchmark.jl - microbenchmarks for the Julia BMSSP implementation.

Run:
    julia --project=../BMSSPAlgorithm benchmark.jl

Requires BenchmarkTools.jl. To install:
    julia -e 'using Pkg; Pkg.add("BenchmarkTools")'
"""

using BenchmarkTools
using Random

include("../BMSSPAlgorithm/src/BMSSPAlgorithm.jl")
using .BMSSPAlgorithm

Random.seed!(42)

"""Generate a sparse random directed graph with n vertices and ~edge_factor*n edges."""
function gen_sparse(n::Int, edge_factor::Int=3)
    g = Graph()
    for i in 1:n
        add_edge!(g, i, i, 0.0)  # ensure node exists
    end
    m = edge_factor * n
    for _ in 1:m
        u = rand(1:n)
        v = rand(1:n)
        if u != v
            add_edge!(g, u, v, float(rand(1:100)))
        end
    end
    return g
end

"""Generate a grid graph with unit weights."""
function gen_grid(width::Int, height::Int)
    g = Graph()
    for y in 0:height-1
        for x in 0:width-1
            u = y * width + x
            if x + 1 < width
                add_edge!(g, u, u + 1, 1.0)
            end
            if y + 1 < height
                add_edge!(g, u, u + width, 1.0)
            end
        end
    end
    return g
end

println("=== BMSSP Julia Benchmarks ===\n")

println("--- run_sssp on sparse random graphs ---")
for n in [100, 500, 1000, 5000]
    g = gen_sparse(n, 3)
    src = first(keys(g.adj))
    b = @benchmark run_sssp($g, $src) samples=10 seconds=10
    println("  n=$n: $(BenchmarkTools.prettytime(time(median(b))))  allocs=$(allocs(median(b)))")
end

println("\n--- run_sssp on grid graphs ---")
for (w, h) in [(10, 10), (20, 20), (50, 50)]
    g = gen_grid(w, h)
    src = first(keys(g.adj))
    b = @benchmark run_sssp($g, $src) samples=10 seconds=10
    println("  $(w)x$(h) ($(w*h) nodes): $(BenchmarkTools.prettytime(time(median(b))))  allocs=$(allocs(median(b)))")
end

println("\n--- DQueue micro-operations ---")
let
    dq = DQueue(10, 100.0)
    b = @benchmark insert!(d, "x", 1.0) setup=(d=DQueue(10, 100.0)) samples=1000
    println("  insert: $(BenchmarkTools.prettytime(time(median(b))))")
end

println("\nDone.")
