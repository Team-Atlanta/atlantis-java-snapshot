FROM nixos/nix:2.28.3 AS nix-builder

RUN mkdir /app
WORKDIR /app

RUN nix-env -iA nixpkgs.python3
RUN nix-env -iA nixpkgs.glibc
RUN nix-env -iA nixpkgs.patchelf

COPY Cargo.toml /app
COPY Cargo.lock /app
COPY flake.nix /app
COPY flake.lock /app
COPY deny.toml /app
COPY taplo.toml /app
COPY build.rs /app
COPY proto /app/proto
COPY src /app/src

COPY scripts/docker-patch.py /app/patch.py
RUN chmod +x /app/patch.py

ENV PATH="/root/.cargo/bin:${PATH}"
RUN nix develop --extra-experimental-features 'flakes nix-command' -c cargo install --path .
RUN /app/patch.py /root/.cargo/bin/code-browser-server

FROM debian:bullseye-slim

RUN mkdir /app
COPY run.sh /app
COPY --from=nix-builder /app/out /app/

WORKDIR /app

