FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build -- --configuration=production

FROM nginx:alpine

# Defaults work for local `docker compose up`.
# On Render these are overridden via the service's env vars.
ENV PORT=80 \
    BACKEND_URL=http://backend:8000

COPY --from=builder /app/www /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80
