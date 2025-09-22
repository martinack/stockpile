# stockpile

Basic stock management for private households.

---

## Purpose

**stockpile** is a simple application to help manage inventory in private households.
The intention is to use it for self made food because it doesn't have barcodes.

Further development will also support standard EAN codes which opens up a wider range of use cases.

---

## Quickstart

1. Create a docker-compose.yml
```yaml
version: "3.9"
name: stockpile

services:
  backend:
    image: martinack/stockpile-backend:latest
    container_name: stockpile-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
      - ./backend/qrcodes:/app/qrcodes
    restart: unless-stopped

  frontend:
    image: martinack/stockpile-web:latest
    container_name: stockpile-frontend
    ports:
      - "8080:80"
    depends_on:
      - backend
    restart: unless-stopped
```

2. Run:
```bash
docker compose pull
docker compose up -d
```
---

## Features

Functional:
* create storage locations
* create items (name, quantity, storage location)
* Create QR codes for items
* Scan a qr-code and remove the items

Technical:
* REST-api for easy data-access
* Web-frontend, optimized for mobile usage
* Docker support

---

## Architecture / Structure

├── backend/ # API / server logic
├── web/ # Frontend (UI)
├── docker-compose.yml # Orchestration
├── .github/ # CI / workflows
└── .gitignore


**Technologies used:**

- Python (backend)
-- fastapi / uvicorn
-- sqlite
- TypeScript / HTML / SCSS (frontend)
-- Angular / Angular Material

---

## Getting Started

## Requirements

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose  
- Node.js & npm/yarn — if running the frontend separately  
- Python & pip — if running the backend directly  

## Development

```bash
# starting frontend
cd web
npm install
npm start

# starting backend
cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Use feature branches for new development.

## Contributing

Contributions are welcome! You can help by:

* Reporting issues or bugs
* Suggesting or implementing new features (e.g. expiry tracking, barcode scanning)
* Improving the frontend UI
* Writing documentation or tests

Please open a pull request or an issue to get started.
