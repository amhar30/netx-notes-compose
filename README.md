# NetX Notes — Docker Compose Assignment

A four-service notes application built with Docker Compose as part of the NetXperts DevOps Internship.

## Architecture

```text
Browser
   |
   | http://localhost:8080
   v
Nginx Reverse Proxy (proxy)
   |
   v
Flask API (api)
   |                 |
   v                 v
PostgreSQL          Redis
   db               cache

Frontend network: proxy, api
Backend network:  api, db, cache (internal)
Persistent data:  pgdata named volume
```

Only Nginx publishes a host port. PostgreSQL and Redis are not directly exposed to the host.

## Quick Start

```bash
git clone https://github.com/amhar30/netx-notes-compose.git
cd netx-notes-compose
cp .env.example .env
docker compose up -d --build
curl http://localhost:8080/health
```

Expected response:

```json
{"status":"ok"}
```

Configure the local `.env` file before starting the application. The actual `.env` file is ignored by Git and must not be committed.

## Task 1 — Containerise the API

* Used `python:3.12-slim`.
* Installed dependencies before copying application code to support Docker layer caching.
* Created a non-root user named `appuser`.
* Used Gunicorn instead of the Flask development server.
* Added `.dockerignore` to exclude unnecessary files from the build context.

Verification:

```bash
docker build -t netx-notes-api:task1 ./api
docker image inspect netx-notes-api:task1 --format 'User={{.Config.User}}'
```

Expected user: `appuser`.

**Evidence:** [Open Task 1 — Docker image build](screenshots/1..png)

## Task 2 — Docker Compose and Nginx

* Configured four services: `proxy`, `api`, `db`, and `cache`.
* Used pinned image tags for Nginx, PostgreSQL, and Redis.
* Published only port `8080` on the host.
* Configured Nginx to forward requests to `api:5000`.
* Mounted the Nginx configuration as read-only.

Verification:

```bash
docker compose config -q
docker compose up -d --build
curl http://localhost:8080/health
```

Expected response:

```json
{"status":"ok"}
```

**Evidence:** [Open Task 2 — Docker Compose startup](screenshots/2.%20docker%20compose%20up%20-d%20--build.png)

## Task 3 — Configuration and Secrets

* Stored database configuration in the local `.env` file.
* Referenced `${POSTGRES_DB}`, `${POSTGRES_USER}`, and `${POSTGRES_PASSWORD}` in `compose.yaml`.
* Added `.env.example` with placeholder values.
* Added `.env` to `.gitignore` to prevent local credentials from being committed.

Verification:

```bash
git check-ignore -v .env
docker compose config -q
```

The actual `.env` file contains local credentials and must not be pushed to GitHub.

**Evidence:** [Open Task 3 — Configuration and secrets](screenshots/3.Configuration%20and%20secrets.png)

## Task 4 — Network Isolation

Created two user-defined Docker networks:

* **Frontend:** connects `proxy` and `api`.
* **Backend:** connects `api`, `db`, and `cache`, with `internal: true`.

The API connects to both networks. Nginx connects only to the frontend network, preventing it from resolving the database service through Docker's network DNS.

Verification:

```bash
docker compose exec proxy ping -c 1 db
docker compose exec api getent hosts db
```

The proxy-to-database isolation test should fail, while the API should successfully resolve the `db` service name.

**Evidence:**

* [Open Task 4 — Database isolation test](screenshots/4.db%20isolation%20check.png)
* [Open Task 4 — API database DNS resolution](screenshots/4.1api%20connection%20with%20db%20check.png)

## Task 5 — Persistent PostgreSQL Data

PostgreSQL uses the named volume `pgdata`, mounted at `/var/lib/postgresql/data`.

Three notes were saved through the API:

* `hello-1`
* `hel`
* `hello-3`

After running `docker compose down` and starting the stack again, all three notes remained available. This demonstrated that the PostgreSQL data persisted when the containers were removed and recreated.

Verification:

```bash
docker compose down
docker compose up -d
curl http://localhost:8080/notes
```

**Evidence:**

* [Open Task 5 — Named volume declaration](screenshots/5.1%20volume%20declaring.png)
* [Open Task 5 — PostgreSQL data persistence](screenshots/5.2%20pg%20data%20saves%20data.png)
* [Open Task 5 — Volume configuration in Compose](screenshots/5.in%20compose%20yaml%2C%20db%20volumes%20added.png)
* [Open Task 5 — Notes before restarting containers](screenshots/5-before-restart.png)
* [Open Task 5 — Notes after restarting containers](screenshots/5-after-restart.png)

### Why does `docker compose down -v` delete the notes?

`docker compose down` removes containers and the Compose network but preserves named volumes by default.

The `-v` option also removes Compose-managed named volumes, including `pgdata`. Removing this volume deletes the persisted PostgreSQL data, so the saved notes are no longer available.

## Task 6 — Healthchecks and Startup Order

Added healthchecks for all four services:

* **PostgreSQL:** `pg_isready`
* **Redis:** `redis-cli ping`
* **API:** Python request to `/health`
* **Nginx:** request to `/health` through the proxy

The API waits for PostgreSQL and Redis to become healthy using `depends_on` with `condition: service_healthy`. Nginx waits for the API to become healthy. All services use `restart: unless-stopped`.

Verification:

```bash
docker compose ps
curl http://localhost:8080/health
```

**Evidence:** [Open Task 6 — All containers healthy](screenshots/6.containers%20are%20healthy.png)

## Task 7 — Scaling and Resource Limits

Scaled the API to three replicas:

```bash
docker compose up -d --build --scale api=3
```

Repeated requests to `/notes` returned different `served_by` values, demonstrating that all three API replicas handled requests through Nginx.

Each API replica has the following resource limits:

* **CPU:** `0.50`
* **Memory:** `256M`

A fixed host port cannot be published by all three API replicas because they would compete for the same host port. The API uses its internal container port, while Nginx publishes port `8080`.

Verification:

```bash
docker compose ps
docker stats --no-stream
```

**Evidence:**

* [Open Task 7 — Three API containers](screenshots/7.scaling%203%20api%20containers.png)
* [Open Task 7 — Load balancing](screenshots/7.1%20load%20balancing.png)
* [Open Task 7 — Resource limits](screenshots/7.2%20resource%20limts.png)

## Problems I Hit

1. **Invalid volume configuration:** Corrected the PostgreSQL volume mapping to `pgdata:/var/lib/postgresql/data` and declared `pgdata` in the top-level `volumes` section.

2. **HTTP 400 when posting JSON:** Requests sent through `curl.exe` in PowerShell initially returned `400 Bad Request`. Using `Invoke-RestMethod` with `ConvertTo-Json -Compress` fixed the JSON request body.

3. **Initial API connection reset:** The first request was made immediately after starting the containers. Retrying after startup completed returned HTTP 200 and `{"status":"ok"}`.

4. **GitHub authentication:** HTTPS Git push rejected password authentication. Using a Personal Access Token resolved the authentication problem.

## Repository

[Open the NetX Notes GitHub repository](https://github.com/amhar30/netx-notes-compose)
