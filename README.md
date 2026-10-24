# Stockpile

Stockpile is a mobile-friendly household inventory application. It creates QR
labels, tracks storage locations and quantities, and checks items out after a
scan. PostgreSQL is the source of truth; Solr is a replaceable search index.

## Run with Docker

Copy the example configuration and set `STOCKPILE_HOST` to the hostname or LAN
IP that browsers will use. Use a strong `POSTGRES_PASSWORD` outside of local
experiments.

```bash
cp .env.example .env
# edit .env: STOCKPILE_HOST=stockpile.lan   (or e.g. 192.168.178.20)
docker compose up -d --build
```

Only Caddy is public. Open `https://<STOCKPILE_HOST>:8443/` (and
`https://<STOCKPILE_HOST>:8443/docs` for the API documentation). HTTP on port
8081 redirects to HTTPS; the frontend, FastAPI, PostgreSQL, and Solr have no
published ports.

Caddy creates an internal, self-signed certificate. The first visit on every
device therefore displays a browser warning. For camera and microphone access,
trust Caddy's local root CA on each device after verifying the fingerprint:

```bash
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./stockpile-caddy-root.crt
```

Import that certificate into the device trust store, then revisit the HTTPS URL.
Do not expose PostgreSQL or Solr to the LAN. To stop services while preserving
inventory data, use `docker compose down`. PostgreSQL, Solr, Caddy state, and
QR images persist in Docker volumes/bind mounts. The old
`backend/data/storage.db` SQLite file is intentionally neither imported nor
deleted; it remains a local backup.

If an operator must rebuild the derived Solr index, use the private backend
container rather than a public HTTP endpoint:

```bash
docker compose exec backend /app/.venv/bin/python -m stockpile.reindex
```

## Development

Requirements: Node.js 22+ (Node 24 is used in CI), Python 3.13+, and
[uv](https://docs.astral.sh/uv/). The backend needs a reachable PostgreSQL
database and Solr collection; the production Compose configuration is the
recommended way to run all services together.

```bash
cd backend
uv sync --group test
uv run pytest -q

cd ../web
npm ci
npm start
```

The Angular development proxy keeps browser calls relative (`/api`) and targets
`http://localhost:9000`; use it only with a separately started development
backend. Production browsers always use Caddy's same-origin HTTPS `/api` route.

## Verification

```bash
# backend API, validation, and real PNG QR generation
cd backend && uv run --group test pytest -q

# Angular production build and unit tests
cd web && npm run build && npm test -- --watch=false

# full PostgreSQL + Solr + Caddy HTTPS smoke test (uses disposable volumes)
docker compose -f docker-compose.yml -f docker-compose.smoke.yml --project-name stockpile-smoke up --build --wait -d
python3 tests/docker_smoke.py
docker compose -f docker-compose.yml -f docker-compose.smoke.yml --project-name stockpile-smoke down --volumes
```

The smoke test deliberately accepts Caddy's untrusted test certificate and
exercises units, warehouses, items, Solr search/facets, QR PNG generation, and
the HTTPS `/api` proxy.
