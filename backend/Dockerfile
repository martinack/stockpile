FROM python:3.13-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    libfreetype6-dev \
    libjpeg-dev \
    libpq-dev \
    libtiff-dev \
    libwebp-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# The container image is not published for linux/arm/v7.  The pinned installer
# selects the matching UV binary for each target platform during Buildx builds.
RUN curl -LsSf https://astral.sh/uv/0.12.10/install.sh -o /tmp/uv-install.sh \
    && UV_UNMANAGED_INSTALL=/usr/local/bin sh /tmp/uv-install.sh \
    && rm /tmp/uv-install.sh

COPY pyproject.toml uv.lock alembic.ini ./
COPY stockpile ./stockpile
COPY migrations ./migrations
RUN uv sync --locked --no-dev

FROM python:3.13-slim AS runtime

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libjpeg62-turbo \
    libpq5 \
    libtiff6 \
    libwebp7 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY stockpile ./stockpile
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD ["/app/.venv/bin/python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health').read()"]
CMD ["sh", "-c", "/app/.venv/bin/alembic upgrade head && exec /app/.venv/bin/uvicorn stockpile.main:app --host 0.0.0.0 --port 8000"]
