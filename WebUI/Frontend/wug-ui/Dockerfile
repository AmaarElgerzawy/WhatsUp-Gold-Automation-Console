# Stage 1: Build React
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: NGINX
FROM nginx:stable-alpine
# Copy files (Check if your build folder is 'dist' or 'build')
COPY --from=build /app/build /usr/share/nginx/html

# Use RUN to create the config file at build time
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
# Only one CMD at the end to start NGINX
CMD ["nginx", "-g", "daemon off;"]
