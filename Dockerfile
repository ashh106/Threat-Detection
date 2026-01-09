# Root dev image for local testing (not used in production)
FROM node:20-bullseye as frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./frontend/
WORKDIR /app/frontend
RUN npm ci --silent
COPY frontend .
RUN npm run build

FROM python:3.11-slim as backend
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend .

FROM nginx:alpine as prod
COPY --from=frontend /app/frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
