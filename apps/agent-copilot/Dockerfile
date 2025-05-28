# Agent Copilot Dockerfile (React)
FROM node:20-alpine as build
WORKDIR /app
COPY package.json package-lock.json* yarn.lock* ./
RUN npm install || yarn install
COPY . .
RUN npm run build || yarn build

FROM node:20-alpine as prod
WORKDIR /app
COPY --from=build /app/build ./build
RUN npm install -g serve
EXPOSE 3001
CMD ["serve", "-s", "build", "-l", "3001"]
