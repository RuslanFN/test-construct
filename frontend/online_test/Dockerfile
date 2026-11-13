# Frontend: сборка Vite -> раздача nginx + проксирование /api на backend
# ---- stage 1: build ----
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- stage 2: serve ----
FROM nginx:1.27-alpine

# Конфиг nginx (SPA + прокси /api)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Собранная статика
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
