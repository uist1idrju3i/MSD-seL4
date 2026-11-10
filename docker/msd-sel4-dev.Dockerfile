# SPDX-License-Identifier: BSD-3-Clause
# Shared development environment for MSD/seL4.
FROM debian:trixie-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4

ARG DEBIAN_SNAPSHOT=20261103T023120Z
ARG RUST_TOOLCHAIN=1.99.1
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL org.opencontainers.image.source="https://github.com/uist1idrju3i/MSD-seL4" \
      org.opencontainers.image.description="MSD/seL4 development tools and test environment" \
      org.opencontainers.image.licenses="BSD-3-Clause"

# Bootstrap CA roots from the default deb.debian.org source before using HTTPS snapshots.
RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY docker/debian.sources /tmp/debian.sources
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources \
    && sed "s/@DEBIAN_SNAPSHOT@/${DEBIAN_SNAPSHOT}/g" /tmp/debian.sources \
        > /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        cmake \
        cpio \
        curl \
        device-tree-compiler \
        file \
        gcc-aarch64-linux-gnu \
        gcc-arm-linux-gnueabi \
        git \
        libxml2-utils \
        ninja-build \
        python3 \
        python3-jinja2 \
        python3-jsonschema \
        python3-lxml \
        python3-ply \
        python3-typing-extensions \
        python3-venv \
        python3-yaml \
        qemu-system-arm \
        rustup \
        xz-utils \
    && rm -rf /var/lib/apt/lists/* /tmp/debian.sources

COPY docker/python-requirements.txt /tmp/python-requirements.txt
RUN python3 -m venv --system-site-packages /opt/sel4-python \
    && /opt/sel4-python/bin/pip install --no-cache-dir --require-hashes \
        -r /tmp/python-requirements.txt \
    && rm -f /tmp/python-requirements.txt \
    && rm -rf /root/.cache

# Rust lives outside HOME so that any host UID passed by docker/msd-sel4-dev
# can use it read-only.
ENV RUSTUP_HOME=/opt/rust/rustup \
    CARGO_HOME=/opt/rust/cargo \
    PATH=/opt/sel4-python/bin:/opt/rust/cargo/bin:${PATH}
RUN rustup toolchain install "${RUST_TOOLCHAIN}" --profile minimal \
        --target armv7a-none-eabi --target aarch64-unknown-none \
    && rustup default "${RUST_TOOLCHAIN}" \
    && chmod -R a+rX /opt/rust \
    && rustc --version \
    && cmake --version | head -1 \
    && ninja --version \
    && arm-linux-gnueabi-gcc --version | head -1 \
    && aarch64-linux-gnu-gcc --version | head -1 \
    && qemu-system-arm --version | head -1 \
    && qemu-system-aarch64 -machine help | grep -Eq '^raspi3b ' \
    && python3 -c 'import jinja2, jsonschema, lxml, ply, pyfdt, typing_extensions, yaml'

# The wrapper runs as the host UID, which may differ from 1000 on CI runners.
RUN groupadd --gid 1000 builder \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/builder \
        --shell /bin/bash builder \
    && chmod 1777 /home/builder
USER builder
WORKDIR /work
