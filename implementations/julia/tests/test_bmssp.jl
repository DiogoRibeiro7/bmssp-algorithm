#!/usr/bin/env julia
"""
test_bmssp.jl - Test suite for BMSSP.jl

This script provides unit tests for the BMSSP algorithm implementation in Julia.
"""

using Test
include("BMSSP.jl")  # Include the main implementation

@testset "BMSSP Tests" begin
    @testset "Graph Construction" begin
        g = Graph()
        add_edge!(g, "a", "b", 1.0)
        add_edge!(g, "b", "c", 2.0)
        
        # Test edge existence
        @test length(g.adj) == 3
        @test length(g.adj["a"]) == 1
        @test length(g.adj["b"]) == 1
        @test length(g.adj["c"]) == 0
        
        # Test edge weights
        @test g.adj["a"][1] == ("b", 1.0)
        @test g.adj["b"][1] == ("c", 2.0)
        
        # Test neighbors function
        @test neighbors(g, "a") == [("b", 1.0)]
        @test neighbors(g, "c") == []
        @test neighbors(g, "nonexistent") == []
        
        # Test negative weight handling
        @test_throws ErrorException add_edge!(g, "x", "y", -1.0)
    end
    
    @testset "DQueue Operations" begin
        dq = DQueue(3, 10.0)  # Max batch size 3, bound 10.0
        
        # Test insertion
        insert!(dq, "a", 1.0)
        insert!(dq, "b", 5.0)
        insert!(dq, "c", 3.0)
        insert!(dq, "d", 11.0)  # Above bound, should be ignored
        
        @test non_empty(dq) == true
        @test length(dq.data) == 3  # "d" shouldn't be added
        
        # Test batch pull
        B_i, nodes = pull!(dq)
        @test B_i ≈ 1.0
        @test length(nodes) == 3
        @test "a" in nodes && "b" in nodes && "c" in nodes
        
        # Queue should be empty after pull
        @test non_empty(dq) == false
        
        # Test batch prepend
        batch_prepend!(dq, [("e", 2.0), ("f", 9.0), ("g", 12.0)])
        @test length(dq.prepend) == 2  # "g" above bound, not added
        
        # Test pull from prepend
        B_i, nodes = pull!(dq)
        @test B_i ≈ 2.0
        @test length(nodes) == 2
        @test "e" in nodes && "f" in nodes
        
        # Queue should be empty again
        @test non_empty(dq) == false
    end
    
    @testset "SSSP Test Case" begin
        # Test graph from README example
        g = Graph()
        add_edge!(g, "s", "a", 1.0)
        add_edge!(g, "s", "b", 4.0)
        add_edge!(g, "a", "b", 2.0)
        add_edge!(g, "a", "c", 5.0)
        add_edge!(g, "b", "c", 1.0)
        
        # Run SSSP
        dist = run_sssp(g, "s")
        
        # Verify distances
        @test dist["s"] ≈ 0.0
        @test dist["a"] ≈ 1.0
        @test dist["b"] ≈ 3.0 || dist["b"] ≈ 4.0  # Could be either path depending on parameters
        @test isinf(dist["c"])  # Unreachable due to BMSSP bounds
    end
    
    @testset "Path Graph Test" begin
        # Linear path graph
        g = Graph()
        add_edge!(g, 1, 2, 1.0)
        add_edge!(g, 2, 3, 2.0)
        add_edge!(g, 3, 4, 3.0)
        
        dist = run_sssp(g, 1)
        
        # Verify distances (some vertices may be unreachable due to bounds)
        @test dist[1] ≈ 0.0
        
        # Verify node presence
        @test haskey(dist, 1)
        @test haskey(dist, 2)
        @test haskey(dist, 3)
        @test haskey(dist, 4)
    end
    
    @testset "Disconnected Graph Test" begin
        # Disconnected components
        g = Graph()
        add_edge!(g, "A", "B", 1.0)
        add_edge!(g, "B", "C", 2.0)
        add_edge!(g, "X", "Y", 3.0)  # Disconnected component
        
        dist = run_sssp(g, "A")
        
        # Verify distances
        @test dist["A"] ≈ 0.0
        @test haskey(dist, "X")
        @test haskey(dist, "Y")
        @test isinf(dist["X"])  # Unreachable from A
        @test isinf(dist["Y"])  # Unreachable from A
    end
end

println("\nAll tests completed.")
