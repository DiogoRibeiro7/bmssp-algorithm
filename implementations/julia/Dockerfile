FROM julia:1.9-bookworm
WORKDIR /app
COPY BMSSPAlgorithm /app/BMSSPAlgorithm
RUN julia -e 'using Pkg; Pkg.activate("/app/BMSSPAlgorithm"); Pkg.instantiate(); Pkg.precompile()'
ENTRYPOINT ["julia", "--project=/app/BMSSPAlgorithm", "/app/BMSSPAlgorithm/src/BMSSPAlgorithm.jl"]
