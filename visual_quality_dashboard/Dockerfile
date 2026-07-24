# Build stage
FROM node:20-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# For React Router to work properly with Nginx, a custom conf is usually needed, 
# but for a simple dashboard it might be fine. We'll add a simple conf later if needed.

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
