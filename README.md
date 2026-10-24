# Stockpile

Stockpile is a mobile-friendly household inventory application for self-made food and other supplies. It creates QR labels, tracks quantities and storage locations, and lets a scanned label be checked out.

## Run with Docker

Docker Compose starts the Angular frontend, FastAPI backend, SQLite database, and QR-code storage:

```bash
docker compose up -d --build
```

- Web UI: <http://localhost:8080>
- Direct API: <http://localhost:9000>
- API documentation: <http://localhost:9000/docs>

The browser uses its own `/api` path. Nginx proxies that path to the backend, so no frontend hostname or API port needs to be configured. SQLite data and generated QR images are kept in `backend/data` and `backend/qrcodes`.

Stop the stack with `docker compose down`. This preserves the bind-mounted inventory data.

## Development

Requirements: Docker for deployment, Node.js 24.15.0 or later for the frontend, and [uv](https://docs.astral.sh/uv/) with Python 3.13 or later for the backend.

```bash
# backend
cd backend
uv sync --group test
uv run uvicorn stockpile.main:app --reload --port 9000

# frontend, in another terminal
cd web
npm ci
npm start
```

The Angular development server proxies `/api` to `http://localhost:9000` through `web/proxy.conf.json`.

## Verification

```bash
# backend API and real QR-image generation
cd backend && uv run --group test pytest

# Angular build and unit tests
cd web && npm run build && npm test

# full Compose smoke test, using disposable Docker volumes
docker compose -f docker-compose.yml -f docker-compose.smoke.yml --project-name stockpile-smoke up --build --wait -d
python3 tests/docker_smoke.py
docker compose -f docker-compose.yml -f docker-compose.smoke.yml --project-name stockpile-smoke down --volumes
```

The smoke test exercises the API only through the frontend proxy, including warehouse and item lifecycle operations and PNG QR-code generation.
