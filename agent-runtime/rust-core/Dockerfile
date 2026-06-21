FROM rust:1.77 as builder

WORKDIR /usr/src/app

# Install protobuf compiler for tonic-build
RUN apt-get update && apt-get install -y protobuf-compiler

COPY . .

# We need proto dir in parent dir context, so this requires a context trick or just copy it
# Since docker-compose context is rust-core, we will assume proto is available if built from monorepo root.
RUN cargo build --release

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /usr/src/app/target/release/agent-runtime .
CMD ["./agent-runtime"]
