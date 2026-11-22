# InternNexus development container

This directory is for local development only. The deployment configuration in
`../docker-compose.yml` is not used or changed by this setup.

## Start

1. Open the repository root in VS Code or Cursor.
2. Select **Reopen in Container** when prompted (or use the command palette).
3. In the container terminal, install the dependencies for the services you
   plan to work on, then run them:

   ```bash
   uv sync --directory backend --group dev
   uv sync --directory pipeline --group dev
   pnpm --dir frontend install --frozen-lockfile

   cd backend && uv run alembic -c alembic.ini upgrade head
   cd backend && uv run uvicorn app.main:app --reload
   cd frontend && pnpm dev
   # Optional ingestion work:
   cd pipeline && uv run internnexus-pipeline
   ```

The container starts a development-only pgvector database named `db`. The
workspace container is configured to use it through `POSTGRES_HOST=db`.

The workspace lives at its host path inside the container — `~/Developer/Ensign/internjobs`,
not `/workspaces/internjobs`. Keep it that way, and keep `workspaceFolder` in
`devcontainer.json` equal to the mount target in `docker-compose.yml`. The reason is bind-mount
resolution: a path handed to the Docker daemon from inside this container is resolved on the
host, and a container-only path does not exist there. Docker answers a missing source by
creating an empty directory and mounting that rather than failing, so whatever asked for it
silently receives nothing. Equal paths on both sides remove the question. It also means stack
traces and tool output name paths you can open directly on the host.

## Docker from inside the container

The `docker` CLI is available and talks to the **host** daemon, not a nested one. Anything you
start this way is a sibling of the workspace container, not a child of it. The host socket is
bound in as `/var/run/docker-host.sock`; the `docker-outside-of-docker` feature puts a
vscode-owned proxy at `/var/run/docker.sock` in front of it, because the bind-mounted socket
itself arrives owned by root and a non-root user cannot write it.

Two consequences worth knowing:

- **Paths are resolved on the host.** `docker run -v $(pwd)/foo:/foo` works only because the
  workspace is mounted at its host path (see above). Keep it that way.
- **Sibling ports are not on `localhost`.** A port published by a container you start from in
  here is reachable at `host.docker.internal`, not `localhost`. `localhost` refuses the
  connection — it is this container.

Note that `../docker-compose.yml` defines its own `db`, and the dev container already runs one.
Bringing the full production stack up from inside here will contend for the same host ports.

## AI coding CLIs

The toolbox image contains `codex`, `opencode`, and `claude`. Authenticate
`codex` and `opencode` from a terminal inside the container on first use:

```bash
codex login
opencode auth login
```

`claude` needs no login: it uses your Claude subscription through
`CLAUDE_CODE_OAUTH_TOKEN`, read from the host environment. Create the token once
on the host with `claude setup-token`, export it from `~/.zshrc`, and restart the
editor so it picks the variable up. Claude's settings and history live in the
`internjobs_claude_data` Docker volume.

Their authentication and session state live in named Docker volumes scoped to
this project. Credentials are never copied into the image, repository, or Git.
The repository's existing `AGENTS.md` remains the shared project guidance for
both tools.

## Rebuild and reset

Use **Dev Containers: Rebuild Container** after changing the Dockerfile. This
keeps the database and agent-authentication volumes. To deliberately reset
development data, stop the dev container and remove its Docker volumes using
your container manager; that is intentionally not automated here.
