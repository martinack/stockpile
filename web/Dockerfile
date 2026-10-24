FROM --platform=$BUILDPLATFORM node:24-alpine AS builder

WORKDIR /app/web

# Install dependencies first (better layer caching)
COPY package*.json ./
RUN npm ci

# Copy the rest of the source
COPY . ./

RUN npm run build -- --configuration production

FROM nginx:1.28-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/web/dist/web/browser/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
