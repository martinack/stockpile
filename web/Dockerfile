# 1) Build stage - force native platform (AMD64) to avoid esbuild emulation issues
FROM --platform=$BUILDPLATFORM node:20-alpine AS builder

WORKDIR /app/web

# Install dependencies first (better layer caching)
COPY package*.json ./
RUN npm ci

# Copy the rest of the source
COPY . ./

# Build Angular app (production)
# If you use a different configuration name, adjust the flag below.
# You can also use: npx ng build --configuration production
RUN npm run build -- --configuration production

# 2) Runtime stage
FROM nginx:1.27-alpine AS runtime

# Replace default nginx config with SPA-friendly config
# - Serves static files
# - Falls back to index.html for client-side routes
RUN rm -f /etc/nginx/conf.d/default.conf
RUN printf '%s\n' \
  'server {' \
  '  listen 80;' \
  '  listen [::]:80;' \
  '  server_name _;' \
  '  root /usr/share/nginx/html;' \
  '  index index.html;' \
  '' \
  '  location / {' \
  '    try_files $uri $uri/ /index.html;' \
  '  }' \
  '' \
  '  # Proxy API requests to backend' \
  '  location /api {' \
  '    proxy_pass http://lager.lan:9000;' \
  '    proxy_http_version 1.1;' \
  '    proxy_set_header Host $host;' \
  '    proxy_set_header X-Real-IP $remote_addr;' \
  '    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
  '    proxy_set_header X-Forwarded-Proto $scheme;' \
  '  }' \
  '' \
  '  # Cache static assets aggressively (tweak as desired)' \
  '  location ~* \.(?:css|js|jpg|jpeg|gif|png|svg|ico|webp|woff2?)$ {' \
  '    expires 30d;' \
  '    access_log off;' \
  '    add_header Cache-Control "public, max-age=2592000, immutable";' \
  '  }' \
  '}' \
  > /etc/nginx/conf.d/default.conf

# Copy build output from builder
# Note:
# - For Angular v17+ default app builds, output is typically dist/<app-name>/browser
# - If your project name differs, adjust the path below accordingly
COPY --from=builder /app/web/dist/web/browser/ /usr/share/nginx/html/

EXPOSE 80

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
