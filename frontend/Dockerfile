# Frontend Dockerfile
FROM node:22-slim AS base

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN corepack enable

WORKDIR /app

# Build arguments (must be passed at build time)
ARG BACKEND_URL
ARG NEXT_PUBLIC_BASE_URL
RUN test -n "$NEXT_PUBLIC_BASE_URL" || (echo "NEXT_PUBLIC_BASE_URL is required" && exit 1)

# Set as environment variables for the build
ENV BACKEND_URL=$BACKEND_URL
ENV NEXT_PUBLIC_BASE_URL=$NEXT_PUBLIC_BASE_URL

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
FROM node:22-slim AS production

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy standalone output (created by next build with output: 'standalone')
COPY --from=base --chown=node:node /app/.next/standalone ./
COPY --from=base --chown=node:node /app/.next/static ./.next/static
COPY --from=base --chown=node:node /app/public ./public

USER node

# Expose port
EXPOSE 3000

# Run the standalone server
CMD ["node", "server.js"]
