# syntax=docker/dockerfile:1.7

# ---------- Base ----------
FROM node:22-alpine AS base
WORKDIR /app

# ---------- Dependencies ----------
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm install

# ---------- Development image ----------
FROM deps AS development
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

# ---------- Build ----------
FROM deps AS build
COPY . .
RUN npm run build

# ---------- Production image (static assets served by nginx) ----------
FROM nginx:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
