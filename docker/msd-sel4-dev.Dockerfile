# SPDX-License-Identifier: BSD-3-Clause
# Shared development environment for MSD/seL4.
FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS capdl-build

ARG DEBIAN_SNAPSHOT=20261109T224401Z
ARG CAPDL_REV=26b8d39c17e99e5423763e9ed292a1d123c39f56
ARG CAPDL_SHA256=0d96b8fe4b0175d3739cf2f2314d717f915da6b4e6f220be9f763a3103356c86
ARG GHC_VERSION=9.10.3
ARG GHC_SHA256=1ac63f04eac0ad551d45cbde38f27e0e3f43ceefd98833fae1fa3f2dbd042367
ARG STACK_VERSION=3.7.1
ARG STACK_SHA256=b6df9168d471d917d955ee80553562ca2b0b3b1aa61cd1256199406c2d8c4eb4
ARG STACK_SNAPSHOT=lts-24.32
ARG STACK_SNAPSHOT_SHA256=35f75b07f0b69b3c3e69fe8f034f3be26b3236826b569b7bfdfb9c8aaf651552
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN test "$(dpkg --print-architecture)" = amd64 \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY docker/debian.sources /tmp/debian.sources
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources \
    && sed "s/@DEBIAN_SNAPSHOT@/${DEBIAN_SNAPSHOT}/g" /tmp/debian.sources \
        > /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        build-essential curl libgmp-dev libnuma-dev libtinfo6 xz-utils zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/debian.sources
WORKDIR /src
# Configure the bindist in-place and remove its source in the same layer.
# hadolint ignore=DL3003
RUN curl --fail --location --retry 5 \
        "https://downloads.haskell.org/~ghc/${GHC_VERSION}/ghc-${GHC_VERSION}-x86_64-deb12-linux.tar.xz" -o ghc.tar.xz \
    && echo "${GHC_SHA256}  ghc.tar.xz" | sha256sum -c - \
    && mkdir ghc \
    && tar -xJf ghc.tar.xz -C ghc --strip-components=1 \
    && cd ghc && ./configure --prefix=/opt/ghc && make install \
    && cd /src && rm -rf ghc ghc.tar.xz
RUN curl --fail --location --retry 5 \
        "https://github.com/commercialhaskell/stack/releases/download/v${STACK_VERSION}/stack-${STACK_VERSION}-linux-x86_64.tar.gz" -o stack.tar.gz \
    && echo "${STACK_SHA256}  stack.tar.gz" | sha256sum -c - \
    && tar -xzf stack.tar.gz --strip-components=1 -C /usr/local/bin \
        "stack-${STACK_VERSION}-linux-x86_64/stack" \
    && rm stack.tar.gz
ENV PATH=/opt/ghc/bin:${PATH}
RUN curl --fail --location --retry 5 \
        "https://codeload.github.com/coliasgroup/capdl/tar.gz/${CAPDL_REV}" -o capdl.tar.gz \
    && echo "${CAPDL_SHA256}  capdl.tar.gz" | sha256sum -c - \
    && mkdir capdl && tar -xzf capdl.tar.gz -C capdl --strip-components=1 \
    && curl --fail --location --retry 5 \
        "https://raw.githubusercontent.com/commercialhaskell/stackage-snapshots/master/lts/$(printf '%s' "${STACK_SNAPSHOT#lts-}" | tr . /).yaml" -o snapshot.yaml \
    && echo "${STACK_SNAPSHOT_SHA256}  snapshot.yaml" | sha256sum -c -
WORKDIR /src/capdl/capDL-tool
RUN stack --system-ghc --no-install-ghc --resolver /src/snapshot.yaml \
        build --jobs 2 --copy-bins --local-bin-path /out \
    && strip /out/parse-capDL \
    && ldd /out/parse-capDL \
    && mkdir -p /out/licenses \
    && cp -r /src/capdl/LICENSES /out/licenses/capdl
RUN mkdir -p /out/licenses/haskell \
    && find /root/.stack/snapshots /opt/ghc/share/doc -type f \
        \( -iname 'license*' -o -iname 'copying*' \) \
        -exec cp --parents '{}' /out/licenses/haskell/ \; \
    && find /src/capdl/capDL-tool -name '*.hs' -not -path '*/.stack-work/*' \
        -exec sed -n '1,8p' '{}' \; > /out/licenses/capdl-copyright.txt \
    && chmod -R a+rX /out/licenses

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2

ARG DEBIAN_SNAPSHOT=20261109T224401Z
# rust-sel4 pins its own nightly; keep it equal to projects/rust-smoke/rust-toolchain.toml.
ARG RUST_SEL4_NIGHTLY=nightly-2026-08-21
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
        build-essential \
        ca-certificates \
        cmake \
        cpio \
        device-tree-compiler \
        file \
        gcc-aarch64-linux-gnu \
        g++-arm-linux-gnueabi \
        gcc-arm-linux-gnueabi \
        git \
        libclang-dev \
        libgmp10 \
        libxml2-utils \
        ninja-build \
        python3 \
        python3-jinja2 \
        python3-jsonschema \
        python3-libarchive-c \
        python3-lxml \
        python3-pyelftools \
        python3-ply \
        python3-typing-extensions \
        python3-venv \
        python3-yaml \
        qemu-system-arm \
        rustup \
    && rm -rf /var/lib/apt/lists/* /tmp/debian.sources

COPY docker/python-requirements.txt /tmp/python-requirements.txt
COPY --from=capdl-build /out/parse-capDL /usr/local/bin/parse-capDL
COPY --from=capdl-build /out/licenses /usr/share/doc/parse-capDL
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
# rust-sel4 builds core with -Z build-std, so no prebuilt target is installed.
RUN rustup toolchain install "${RUST_SEL4_NIGHTLY}" --profile minimal \
        --component rust-src --component llvm-tools-preview \
    && rustup default "${RUST_SEL4_NIGHTLY}" \
    && chmod -R a+rX /opt/rust \
    && rustc --version \
    && cmake --version | head -1 \
    && ninja --version \
    && arm-linux-gnueabi-gcc --version | head -1 \
    && aarch64-linux-gnu-gcc --version | head -1 \
    && qemu-system-arm --version | head -1 \
    && qemu-system-aarch64 -machine help | grep -Eq '^raspi3b ' \
    && python3 -c 'import elftools, jinja2, jsonschema, libarchive, lxml, ply, pyfdt, typing_extensions, yaml'

# The wrapper runs as the host UID, which may differ from 1000 on CI runners.
RUN groupadd --gid 1000 builder \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/builder \
        --shell /bin/bash builder \
    && chmod 1777 /home/builder
USER builder
WORKDIR /work
