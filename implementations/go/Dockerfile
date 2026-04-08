# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /src
COPY go.mod ./
COPY *.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /bmssp .

# Runtime stage
FROM scratch
COPY --from=builder /bmssp /bmssp
ENTRYPOINT ["/bmssp"]
