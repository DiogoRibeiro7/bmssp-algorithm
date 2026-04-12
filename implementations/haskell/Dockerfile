FROM haskell:9.4 AS builder

WORKDIR /build
COPY bmssp.cabal .
COPY src ./src
COPY app ./app
RUN cabal update && cabal build

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgmp10 libffi8 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/dist-newstyle/build/*/ghc-*/bmssp-*/x/bmssp/build/bmssp/bmssp /usr/local/bin/bmssp
ENTRYPOINT ["/usr/local/bin/bmssp"]
