# Build stage
FROM gcc:13 AS builder
WORKDIR /src
COPY bmssp.f90 Makefile ./
RUN gfortran -Wall -Wextra -std=f2008 -O2 bmssp.f90 -o /bmssp

# Runtime stage
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgfortran5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /bmssp /usr/local/bin/bmssp
ENTRYPOINT ["/usr/local/bin/bmssp"]
