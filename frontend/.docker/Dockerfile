# ---------- Node base stage ----------
FROM node:lts-alpine AS base-stage-node
ARG RELEASE
ENV SENTRY_RELEASE=$RELEASE

WORKDIR /code
ENV PATH /code/node_modules/.bin:$PATH
COPY . .
RUN npm i --no-progress --non-interactive

# ---------- Frontend build: dev ----------
FROM base-stage-node AS build-dev
RUN npm run build-dev

# ---------- Frontend build: prod ----------
FROM base-stage-node AS build-prod
RUN npm run build-prod

# ---------- NGINX ----------
FROM nginx:stable-alpine AS nginx-base
COPY ./nginx/base.conf /etc/nginx/conf.d/base.conf

# ---------- NGINX: local ----------
FROM nginx-base AS nginx-local
COPY ./nginx/nginx.local.conf /etc/nginx/conf.d/default.conf
COPY --from=build-dev /code/dist /usr/share/nginx/html
CMD ["nginx", "-g", "daemon off;"]

# ---------- NGINX: dev ----------
FROM nginx-base AS nginx-dev
COPY ./nginx/nginx.dev.conf /etc/nginx/conf.d/default.conf
COPY --from=build-prod /code/dist /usr/share/nginx/html
CMD ["nginx", "-g", "daemon off;"]

# ---------- NGINX: prod ----------
FROM nginx-base AS nginx-prod
COPY ./nginx/nginx.prod.conf /etc/nginx/conf.d/default.conf
COPY --from=build-prod /code/dist /usr/share/nginx/html
CMD ["nginx", "-g", "daemon off;"]
