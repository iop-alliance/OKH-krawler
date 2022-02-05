# ------------------------------------------------------------------------------
# Build Stage
# ------------------------------------------------------------------------------

FROM python:3.10-alpine AS builder

# install build dependencies
RUN set -x \
    && apk add --no-cache --no-progress \
        build-base \
        libffi-dev \
        openssl-dev \
    && pip install poetry

WORKDIR /opt/krawler
COPY pyproject.toml poetry.lock /opt/krawler/
COPY krawl/cli/__main__.py /opt/krawler/krawl/cli/

# install build/runtime dependencies
RUN set -x \
    && poetry config virtualenvs.in-project true \
    && poetry install -n --no-ansi --no-dev



# ------------------------------------------------------------------------------
# Final Stage
# ------------------------------------------------------------------------------

FROM python:3.10-alpine

WORKDIR /opt/krawler
COPY --from=builder /opt/krawler/ /opt/krawler/
COPY . /opt/krawler/
ENV PATH="/opt/krawler/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

RUN set -x \
    # install runtime dependencies
    && apk add --no-cache --no-progress \
        libffi \
        openssl

ENTRYPOINT ["/opt/krawler/.venv/bin/krawl"]
