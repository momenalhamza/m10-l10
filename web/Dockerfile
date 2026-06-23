# Lab 10 — frontend Dockerfile (multi-stage, node:20-alpine).
#
# The builder installs deps and produces the Next.js standalone bundle;
# the runner ships only that self-contained server (~150 MB target,
# well under the 400 MB cap).

# ---- Builder ----
FROM node:20-alpine AS builder
WORKDIR /app

# libc6-compat lets the @next/swc-linux-x64-gnu binary locked in
# package-lock.json load on alpine's musl libc.
RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_* values are baked into the client bundle at build time.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ---- Runner ----
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# next.config.js sets `output: 'standalone'`, writing a self-contained
# server under .next/standalone that runs without node_modules.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
