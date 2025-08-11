#!/usr/bin/env julia
"""
BMSSP.jl - Breaking the Sorting Barrier for Directed Single-Source Shortest Paths

Julia implementation of the BMSSP algorithm from:
"Breaking the Sorting Barrier for Directed Single-Source Shortest Paths"
(arXiv:2504.17033v2, 2025)

This implementation follows the structure of the original algorithm presented in the paper,
with the following components:
- Graph data structure with adjacency lists
- DQueue for bounded batch operations
- FindPivots for pivot selection (Lemma 3.2)
- BaseCase for small-instance solving
- BMSSP main recursive algorithm
"""

module BMSSPAlgorithm

using DataStructures

"""
Represents a directed graph with non-negative edge weights.
"""
mutable struct Graph
    adj::Dict{Any, Vector{Tuple{Any, Float64}}}
    
    # Constructor for empty graph
    function Graph()
        new(Dict{Any, Vector{Tuple{Any, Float64}}}())
    end
end

"""
Add an edge from u to v with weight w.
"""
function add_edge!(g::Graph, u, v, w::Float64)
    if w < 0
        error("Only non-negative weights allowed")
    end
    
    # Add edge u->v with weight w
    if !haskey(g.adj, u)
        g.adj[u] = Tuple{Any, Float64}[]
    end
    push!(g.adj[u], (v, w))
    
    # Ensure v exists in adjacency list
    if !haskey(g.adj, v)
        g.adj[v] = Tuple{Any, Float64}[]
    end
end

"""
Get all neighbors of a vertex u.
"""
function neighbors(g::Graph, u)
    if haskey(g.adj, u)
        return g.adj[u]
    else
        return Tuple{Any, Float64}[]
    end
end

"""
DQueue is a specialized queue structure for batch operations with a distance bound B.
"""
mutable struct DQueue
    M::Int                        # Max nodes to pull per batch
    B::Float64                    # Distance threshold
    data::PriorityQueue{Any, Float64}  # Main priority queue
    prepend::Vector{Tuple{Any, Float64}}  # Batch prepending list
    
    function DQueue(M::Int, B::Float64)
        new(M, B, PriorityQueue{Any, Float64}(), Tuple{Any, Float64}[])
    end
end

"""
Insert a node with its distance into the DQueue.
"""
function insert!(dq::DQueue, node, dist::Float64)
    if dist >= dq.B
        return
    end
    enqueue!(dq.data, node, dist)
end

"""
Batch prepend items to the DQueue.
"""
function batch_prepend!(dq::DQueue, items::Vector{Tuple{Any, Float64}})
    for (node, dist) in items
        if dist < dq.B
            push!(dq.prepend, (node, dist))
        end
    end
end

"""
Check if DQueue is non-empty.
"""
function non_empty(dq::DQueue)
    return !isempty(dq.data) || !isempty(dq.prepend)
end

"""
Pull up to M nodes from DQueue, grouped by distance.
"""
function pull!(dq::DQueue)
    # First try prepend list
    if !isempty(dq.prepend)
        take = min(dq.M, length(dq.prepend))
        group = dq.prepend[1:take]
        dq.prepend = dq.prepend[(take+1):end]
        
        B_i = isempty(group) ? dq.B : group[1][2]
        nodes = Set{Any}([node for (node, _) in group])
        
        return B_i, nodes
    end
    
    # Then try main queue
    if isempty(dq.data)
        return dq.B, Set{Any}()
    end
    
    out = Tuple{Any, Float64}[]
    while !isempty(dq.data) && length(out) < dq.M
        node = dequeue_pair!(dq.data)
        push!(out, node)
    end
    
    B_i = isempty(out) ? dq.B : out[1][2]
    nodes = Set{Any}([node for (node, _) in out])
    
    return B_i, nodes
end

"""
Base case algorithm for small instances.
"""
function base_case(graph::Graph, B::Float64, S::Set{Any}, 
                   d_hat::Dict{Any, Float64}, complete::Set{Any}, k::Int)
    if isempty(S)
        return B, Set{Any}()
    end
    
    x = first(S)
    U0 = Set{Any}([x])
    H = PriorityQueue{Any, Float64}()
    enqueue!(H, x, d_hat[x])
    visited = Set{Any}()
    
    while !isempty(H) && length(U0) < k + 1
        du, u = peek(H)
        dequeue!(H)
        
        if u in visited
            continue
        end
        
        push!(visited, u)
        push!(U0, u)
        push!(complete, u)
        
        for (v, w) in neighbors(graph, u)
            if du + w <= get(d_hat, v, Inf) && du + w < B
                d_hat[v] = du + w
                enqueue!(H, v, d_hat[v])
            end
        end
    end
    
    if length(U0) <= k
        return B, U0
    else
        B_prime = maximum([d_hat[v] for v in U0])
        subset = Set{Any}([v for v in U0 if d_hat[v] < B_prime])
        return B_prime, subset
    end
end

"""
Find pivots using bounded expansion (Lemma 3.2).
"""
function find_pivots(graph::Graph, B::Float64, S::Set{Any}, 
                     d_hat::Dict{Any, Float64}, complete::Set{Any}, k::Int)
    W = copy(S)
    W_prev = copy(S)
    
    # k iterations of bounded expansion
    for _ in 1:k
        W_i = Set{Any}()
        
        for u in W_prev
            du = get(d_hat, u, Inf)
            if du >= B
                continue
            end
            
            for (v, w) in neighbors(graph, u)
                if du + w <= get(d_hat, v, Inf) && du + w < B
                    d_hat[v] = du + w
                    if du + w < B
                        push!(W_i, v)
                    end
                end
            end
        end
        
        union!(W, W_i)
        
        # Size check
        if length(W) > k * length(S)
            return S, W
        end
        
        W_prev = W_i
    end
    
    # Build the forest structure
    F_children = Dict{Any, Vector{Any}}()
    indeg = Dict{Any, Int}()
    
    for u in W
        if !haskey(F_children, u)
            F_children[u] = Any[]
        end
        if !haskey(indeg, u)
            indeg[u] = 0
        end
    end
    
    for u in W
        du = d_hat[u]
        for (v, w) in neighbors(graph, u)
            if v in W && isapprox(d_hat[v], du + w, atol=1e-12)
                push!(F_children[u], v)
                indeg[v] = get(indeg, v, 0) + 1
            end
        end
    end
    
    # Recursive subtree size calculation
    function subtree_size(u)
        size = 1
        for child in F_children[u]
            size += subtree_size(child)
        end
        return size
    end
    
    # Select pivots with subtree size ≥ k and no incoming edges
    P = Set{Any}()
    for u in S
        if get(indeg, u, 0) == 0 && subtree_size(u) >= k
            push!(P, u)
        end
    end
    
    # If no pivots found, use all sources
    if isempty(P)
        return S, W
    end
    
    return P, W
end

"""
Main BMSSP (Bounded Multi-Source Shortest Path) algorithm.
"""
function bmssp(graph::Graph, l::Int, B::Float64, S::Set{Any}, 
               d_hat::Dict{Any, Float64}, complete::Set{Any}, k::Int, t::Int)
    if l == 0
        return base_case(graph, B, S, d_hat, complete, k)
    end
    
    # Find pivots
    P, W = find_pivots(graph, B, S, d_hat, complete, k)
    
    # Initialize DQueue
    M = 2^((l - 1) * t)
    D = DQueue(M, B)
    
    for x in P
        insert!(D, x, d_hat[x])
    end
    
    # Main loop
    U = Set{Any}()
    B0_prime = B
    
    for x in P
        if d_hat[x] < B0_prime
            B0_prime = d_hat[x]
        end
    end
    
    while length(U) < k * (2^(l * t)) && non_empty(D)
        Bi, Si = pull!(D)
        B_prime_i, U_i = bmssp(graph, l - 1, Bi, Si, d_hat, complete, k, t)
        
        union!(U, U_i)
        
        K = Tuple{Any, Float64}[]
        
        for u in U_i
            for (v, w) in neighbors(graph, u)
                if d_hat[u] + w <= get(d_hat, v, Inf)
                    d_hat[v] = d_hat[u] + w
                    
                    if Bi <= d_hat[v] < B
                        insert!(D, v, d_hat[v])
                    elseif B_prime_i <= d_hat[v] < Bi
                        push!(K, (v, d_hat[v]))
                    end
                end
            end
        end
        
        # Prepend K and eligible Si
        prepend_items = K
        for x in Si
            if B_prime_i <= d_hat[x] < Bi
                push!(prepend_items, (x, d_hat[x]))
            end
        end
        
        batch_prepend!(D, prepend_items)
    end
    
    # Final result
    B_prime = min(B0_prime, B)
    
    for x in W
        if get(d_hat, x, Inf) < B_prime
            push!(U, x)
        end
    end
    
    union!(complete, U)
    return B_prime, U
end

"""
Run BMSSP from a single source.
"""
function run_sssp(graph::Graph, source)
    n = length(graph.adj)
    
    # Algorithm parameters
    k = max(1, Int(floor(log2(n)^(1/3))))
    t = max(1, Int(floor(log2(n)^(2/3))))
    l = Int(ceil(log2(n) / t))
    
    # Initialize distances
    d_hat = Dict{Any, Float64}()
    for v in keys(graph.adj)
        d_hat[v] = Inf
    end
    d_hat[source] = 0.0
    
    # Initialize complete set
    complete = Set{Any}([source])
    
    # Run BMSSP
    bmssp(graph, l, Inf, Set{Any}([source]), d_hat, complete, k, t)
    
    return d_hat
end

"""
Example usage and testing.
"""
function main()
    # Create test graph
    g = Graph()
    add_edge!(g, "s", "a", 1.0)
    add_edge!(g, "s", "b", 4.0)
    add_edge!(g, "a", "b", 2.0)
    add_edge!(g, "a", "c", 5.0)
    add_edge!(g, "b", "c", 1.0)
    
    # Run SSSP
    dist = run_sssp(g, "s")
    
    # Print results
    println("Distances from s:")
    for (node, distance) in sort(collect(dist))
        if distance == Inf
            println("  $node: ∞")
        else
            println("  $node: $distance")
        end
    end
end

end # module BMSSPAlgorithm
