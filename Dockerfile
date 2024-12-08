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
    && \
    pip install --no-cache-dir poetry==1.8.5

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
COPY --from=builder /opt/krawler/ /opt/krawler/
COPY . /opt/krawler/
ENV PATH="/opt/krawler/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# install runtime dependencies
RUN install_packages \
        libffi8 \
        openssl

ENTRYPOINT ["/opt/krawler/.venv/bin/krawl"]
