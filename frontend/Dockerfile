FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 3000
RUN sed -i 's/listen\s*80;/listen 3000;/' /etc/nginx/conf.d/default.conf
CMD ["nginx", "-g", "daemon off;"]
