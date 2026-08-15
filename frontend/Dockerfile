FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY vite.config.ts ./
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
# Proxy /api dari container frontend menuju service backend (bukan localhost).
ENV VITE_PROXY_TARGET=http://backend:8000
EXPOSE 5173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]