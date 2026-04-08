# Build stage
FROM rust:1.75-alpine AS builder
RUN apk add --no-cache musl-dev
WORKDIR /src
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release && \
    cp target/release/bmssp /bmssp && \
    strip /bmssp

# Runtime stage
FROM scratch
COPY --from=builder /bmssp /bmssp
ENTRYPOINT ["/bmssp"]
