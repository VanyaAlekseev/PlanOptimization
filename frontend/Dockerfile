FROM node:20-alpine AS build
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* /app/
RUN npm ci || npm install

COPY frontend /app
RUN npm install && npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
# Normalize line endings in nginx config (helps if edited on Windows).
RUN sed -i 's/\r$//' /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

