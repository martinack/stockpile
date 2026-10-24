# Stockpile web frontend

The Angular 22 frontend makes only relative `/api` requests. In production,
Caddy terminates HTTPS and routes `/api/*` to the private FastAPI container;
Nginx serves only the Angular files. This keeps the browser on one HTTPS origin.

## Development

Use Node.js 22 or newer:

```bash
npm ci
npm start
```

Open <http://localhost:4200>. The development proxy maps `/api` to a separately
started backend at `http://localhost:9000`; it is not part of the production
Docker deployment.

## Checks

```bash
npm run build
npm test -- --watch=false
```
