# Frontend Dockerfile
ARG NODE_IMAGE=node:26.13.1-slim@sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc
FROM ${NODE_IMAGE} AS base

ARG VCS_REF=unknown

RUN npm install --global pnpm@12.21.0

WORKDIR /app

# Build arguments (must be passed at build time)
ARG BACKEND_URL
ARG NEXT_PUBLIC_BASE_URL
ARG NEXT_PUBLIC_ENABLE_CREDENTIAL_AUTH
RUN test -n "$NEXT_PUBLIC_BASE_URL" || (echo "NEXT_PUBLIC_BASE_URL is required" && exit 1)

# Set as environment variables for the build
ENV BACKEND_URL=$BACKEND_URL
ENV NEXT_PUBLIC_BASE_URL=$NEXT_PUBLIC_BASE_URL
ENV NEXT_PUBLIC_ENABLE_CREDENTIAL_AUTH=$NEXT_PUBLIC_ENABLE_CREDENTIAL_AUTH

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy application code
COPY . .

# Build the application
RUN pnpm run build

# Create public directory placeholder if it doesn't exist
RUN mkdir -p /app/public

# Production stage with standalone output
# Use Node.js slim image since standalone output requires Node.js runtime
FROM ${NODE_IMAGE} AS production

ARG VCS_REF=unknown
LABEL org.opencontainers.image.revision=$VCS_REF

WORKDIR /app

# The compose health check runs every 30s. Using curl avoids spawning a full
# Node runtime (and its ~40 MB RSS) just to make one HTTP request.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy standalone output (created by next build with output: 'standalone')
COPY --from=base --chown=node:node /app/.next/standalone ./
COPY --from=base --chown=node:node /app/.next/static ./.next/static
COPY --from=base --chown=node:node /app/public ./public

USER node

# Expose port
EXPOSE 3000

# Run the standalone server
CMD ["node", "server.js"]
