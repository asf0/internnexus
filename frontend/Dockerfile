# Frontend Dockerfile
FROM oven/bun:1 AS base

WORKDIR /app

# Copy package files
COPY package.json bun.lock ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy application code
COPY . .

# Build the application
# Env vars will be read at build time from environment (in CI/CD)
# For runtime, we use standalone output which reads env vars at container startup
RUN bun run build

# Create public directory placeholder if it doesn't exist
RUN mkdir -p /app/public

# Production stage with standalone output
# Use Node.js slim image since standalone output requires Node.js runtime
FROM node:20-slim AS production

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy standalone output (created by next build with output: 'standalone')
COPY --from=base /app/.next/standalone ./
COPY --from=base /app/.next/static ./.next/static
COPY --from=base /app/public ./public

# Expose port
EXPOSE 3000

# Run the standalone server
# This reads env vars at runtime, not build time (secure!)
CMD ["node", "server.js"]
