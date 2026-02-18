FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json /app/package.json
RUN npm install

COPY . /app
RUN npm run build


FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Next.js "standalone" output already bundles required node_modules.
COPY --from=builder /app/.next/standalone /app
COPY --from=builder /app/.next/static /app/.next/static
COPY --from=builder /app/public /app/public

EXPOSE 3000
CMD ["node", "server.js"]

