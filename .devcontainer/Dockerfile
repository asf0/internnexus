# Development-only toolbox image. Production images remain in backend/, frontend/,
# and pipeline/ and are intentionally not used here.
FROM node:26.13.1-bookworm@sha256:b7087bc4d973034b30854b378ba107f9fab622b47514cb7e2592e41b8bab8d49 AS node
FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv

FROM mcr.microsoft.com/devcontainers/python:3.14-bookworm

COPY --from=node /usr/local/bin/node /usr/local/bin/
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
COPY --from=uv /uv /uvx /usr/local/bin/

# Keep globally installed developer CLIs writable by the user VS Code connects as.
# Codex's in-place updater otherwise cannot replace a root-owned /usr/local install.
ENV NPM_CONFIG_PREFIX=/home/vscode/.npm-global \
    PATH=/home/vscode/.npm-global/bin:${PATH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev postgresql-client \
    && install -d -m 0755 /etc/apt/keyrings /home/vscode/.local/share \
    && chown vscode:vscode /home/vscode/.local /home/vscode/.local/share \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && install -d -o vscode -g vscode /home/vscode/.npm-global \
    && runuser -u vscode -- npm install --global pnpm@12.21.0 @openai/codex@latest @opencode/cli@latest @anthropic-ai/claude-code@latest \
    && pw_version=$(runuser -u vscode -- npm view @playwright/mcp@latest dependencies.playwright) \
    && runuser -u vscode -- npx -y "playwright@${pw_version}" install chromium \
    && npx -y "playwright@${pw_version}" install-deps chromium \
    && runuser -u vscode -- npm cache clean --force

# backend/.venv and pipeline/.venv are named Docker volumes that persist across
# rebuilds, but a uv-managed interpreter lives under ~/.local/share/uv/python, which
# is part of the image layer and is wiped on every rebuild — a Dockerfile bump like
# 3.12 -> 3.14 leaves the persisted venvs symlinked to a Python that no longer
# exists. Pin uv to the interpreter this image already ships instead.
ENV UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system
