# Stockpile web frontend

This Angular 22 application is served by Nginx in Docker and uses relative `/api` URLs. In Docker, Nginx proxies those calls to the backend. During development, `proxy.conf.json` proxies them to `http://localhost:9000`.

## Development

Use Node.js 24.15.0 or newer:

```bash
npm ci
npm start
```

Open <http://localhost:4200>. Start the backend on port 9000 first if you need API calls.

## Checks

```bash
npm run build
npm test
```
