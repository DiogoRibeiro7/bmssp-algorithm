# Build stage
FROM gcc:13 AS builder
WORKDIR /src
COPY bmssp.c Makefile ./
RUN gcc -Wall -Wextra -std=c11 -O2 bmssp.c -lm -o /bmssp

# Runtime stage
FROM debian:bookworm-slim
COPY --from=builder /bmssp /usr/local/bin/bmssp
ENTRYPOINT ["/usr/local/bin/bmssp"]
