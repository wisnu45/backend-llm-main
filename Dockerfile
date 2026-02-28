FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install -g pnpm
RUN pnpm install

COPY . .
RUN pnpm run build

FROM nginx:alpine AS runner

# Hapus default config nginx
RUN rm -rf /usr/share/nginx/html/*

# Copy hasil build Vite ke nginx folder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx config (optional)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
