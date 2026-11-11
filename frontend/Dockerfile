# Front-end: compila com Node e entrega o dist numa imagem do Caddy. Contexto de build: frontend/.
FROM node:26 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2.11.9
# O Caddyfile vem montado pelo docker-compose.yml.
COPY --from=build /app/dist /srv
