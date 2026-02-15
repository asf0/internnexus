# Frontend Dockerfile
FROM oven/bun:1 AS base

WORKDIR /app

# Build arguments (must be passed at build time)
ARG BACKEND_URL
ARG NEXT_PUBLIC_BASE_URL

# Set as environment variables for the build
ENV BACKEND_URL=$BACKEND_URL
ENV NEXT_PUBLIC_BASE_URL=$NEXT_PUBLIC_BASE_URL

# Copy package files
COPY package.json bun.lock ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy application code
COPY . .

# Build the application
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
CMD ["node", "server.js"]
