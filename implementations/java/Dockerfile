# Build stage
FROM eclipse-temurin:17-jdk AS builder
WORKDIR /src
COPY BMSSP.java ./
RUN javac BMSSP.java

# Runtime stage
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=builder /src/*.class ./
ENTRYPOINT ["java", "BMSSP"]
