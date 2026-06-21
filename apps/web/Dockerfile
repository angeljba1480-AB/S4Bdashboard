FROM node:20-slim AS base
WORKDIR /app

# Install deps (web is self-contained; shared types resolved via tsconfig paths)
COPY apps/web/package.json apps/web/package.json
COPY packages packages
WORKDIR /app/apps/web
RUN npm install

WORKDIR /app
COPY apps/web apps/web

WORKDIR /app/apps/web
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
