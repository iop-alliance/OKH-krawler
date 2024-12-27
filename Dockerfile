# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: CC0-1.0

# syntax=docker/dockerfile:1
# NOTE Lint this file with https://hadolint.github.io/hadolint/

# ------------------------------------------------------------------------------
# Build Stage
# ------------------------------------------------------------------------------

FROM bitnami/python:3.13-debian-12 AS builder

# install build dependencies
RUN install_packages \
        build-essential \
        libffi-dev \
        libssl-dev \
        tar \
        wget \
    && \
    pip install --no-cache-dir poetry==1.8.5

WORKDIR /usr/local/bin

RUN wget --quiet -O sanitize-v1-yaml \
    "https://github.com/OPEN-NEXT/LOSH-OKH-tool/raw/refs/heads/master/run/sanitize-v1-yaml" && \
    chmod +x sanitize-v1-yaml

# Set parameters like so:
# docker build \
#     --build-arg okh_tool_release="0.5.3" \
#     --build-arg some_other_var="bla/blu.bli" \
#     .
ARG okh_tool_release=0.5.3

ENV OKH_TOOL_PKG="okh-tool-$okh_tool_release-x86_64-unknown-linux-musl"
ENV OKH_TOOL_DL="https://github.com/OPEN-NEXT/LOSH-OKH-tool/releases/download/$okh_tool_release/$OKH_TOOL_PKG.tar.gz"
RUN if ! [ -f okh-tool ] ; \
    then \
        wget --quiet "$OKH_TOOL_DL" && \
        tar xf $OKH_TOOL_PKG.tar.gz && \
        mv $OKH_TOOL_PKG/okh-tool ./ && \
        rm $OKH_TOOL_PKG.tar.gz && \
        rm -Rf $OKH_TOOL_PKG ; \
    fi

WORKDIR /opt/krawler
COPY \
    pyproject.toml \
    poetry.lock \
    /opt/krawler/
COPY \
    krawl/cli/__main__.py \
    /opt/krawler/krawl/cli/

# install build/runtime dependencies
RUN poetry config virtualenvs.in-project true &&  \
    poetry install -n --no-ansi --only main

# ------------------------------------------------------------------------------
# Final Stage
# ------------------------------------------------------------------------------

FROM bitnami/python:3.13-debian-12

WORKDIR /opt/krawler
COPY --from=builder /usr/local/bin/okh-tool /usr/local/bin/sanitize-v1-yaml /usr/local/bin/
COPY --from=builder /opt/krawler/ /opt/krawler/
COPY . /opt/krawler/
ENV PATH="/opt/krawler/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# install runtime dependencies
RUN install_packages \
        libffi8 \
        openssl

ENTRYPOINT ["/opt/krawler/.venv/bin/krawl"]
