# Multi-stage build for the C++ BMSSP implementation
FROM gcc:13 AS builder

WORKDIR /build
COPY bmssp.cpp .
RUN g++ -Wall -Wextra -std=c++17 -O2 bmssp.cpp -o bmssp

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/bmssp /usr/local/bin/bmssp
ENTRYPOINT ["/usr/local/bin/bmssp"]
