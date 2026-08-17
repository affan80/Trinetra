# Trinetra

Trinetra is a containerized OSINT investigation platform. The default V1 stack
provides the API, Redis, and the analyst TUI. The legacy pipeline additionally
starts Kafka, Spark, crawler, worker, PostGIS, Neo4j, and MinIO.

## Choose a stack

Use one stack at a time: both publish the API on port `8000`.

| Stack | Compose file | Use it for |
| --- | --- | --- |
| **V1 (recommended)** | `docker-compose.v1.yml` | Multimodal investigations and the Textual analyst TUI |
| Legacy pipeline | `docker-compose.yml` | Kafka/Spark ingestion, crawler, and supporting data services |

## Run V1 from scratch (recommended)

### 1. Install prerequisites

- Docker Engine 24+ with the Docker Compose plugin (`docker compose version`)
- Python 3.11, only if you want to run the host-side TUI

On Linux, allow your user to run Docker without `sudo`, then **sign out and
sign back in** (or reboot):

```bash
sudo usermod -aG docker "$USER"
```

Verify the installation:

```bash
docker version
docker compose version
docker ps
```

If `docker ps` reports permission denied, the group change has not taken effect
yet. Start a new login session, or use `sudo docker ...` for the commands below.

### 2. Start the API and Redis

From the repository root:

```bash
docker compose -f docker-compose.v1.yml up -d --build
docker compose -f docker-compose.v1.yml ps
```

Expected status:

```text
NAME                 STATUS
trinetra-api-1       Up
trinetra-redis-1     Up (healthy)
```

Check the API:

```bash
curl --fail http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/
```

The health response should contain `"status":"healthy"`. Interactive API
documentation is available at <http://127.0.0.1:8000/docs>.

### 3. Start the analyst TUI

The TUI runs on your host terminal and connects to the API at
`http://127.0.0.1:8000` by default.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-v1.txt
python -m tui.app.main
```

In the TUI, select an intake type, enter a title and target, then provide one
of the following:

- **Upload**: a readable local path to an image, video, audio file, PDF, or document
- **URL**: a public `http` or `https` URL
- **Text**: analyst-provided text

Useful keyboard shortcuts: `1` dashboard, `2` new investigation, `4` evidence,
`7` media analysis, `R` report, `L` agent logs, and `Q` quit.

To point the TUI at a different API host:

```bash
TRINETRA_API_URL=http://server-name:8000 python -m tui.app.main
```

### 4. View live service output

```bash
docker compose -f docker-compose.v1.yml logs -f --tail=100
```

Stop the V1 stack while retaining investigation artifacts:

```bash
docker compose -f docker-compose.v1.yml down
```

To delete the V1 containers **and all persisted raw investigation artifacts**:

```bash
docker compose -f docker-compose.v1.yml down -v
```

## Run the legacy pipeline from scratch

First stop V1 if it is running, because both stacks use port `8000`:

```bash
docker compose -f docker-compose.v1.yml down
```

Build and start the full pipeline:

```bash
docker compose up -d --build
docker compose ps
```

Monitor services in a terminal-style view:

```bash
watch -n 2 'docker compose ps'
```

Follow the services most likely to expose startup errors:

```bash
docker compose logs -f --tail=100 api crawler spark-processor worker
```

Verify the API after the services have started:

```bash
curl --fail http://127.0.0.1:8000/health
```

Expected service behaviour:

| Service | Expected status |
| --- | --- |
| `api`, `worker`, `spark-master`, `spark-worker`, `spark-processor` | `Up` |
| `redis` | `Up (healthy)` |
| `kafka`, `zookeeper`, `postgis`, `neo4j`, `minio` | `Up` |
| `crawler` | `Exited (0)` after its bounded crawl, or `Up` while crawling |

`crawler` uses `restart: on-failure`; it must not continuously restart after a
successful crawl. If any service shows `Restarting` or `Exited (1)`, capture its
last logs before changing configuration:

```bash
docker compose logs --tail=200 crawler spark-processor api worker
```

Service URLs and local development credentials:

| Service | Address | Credentials |
| --- | --- | --- |
| API | <http://localhost:8000/docs> | None |
| Spark master | <http://localhost:8080> | None |
| MinIO console | <http://localhost:9001> | `minioadmin` / `minioadmin` |
| Neo4j browser | <http://localhost:7474> | `neo4j` / `password` |
| PostGIS | `localhost:5432` | `osint_user` / `osint_password` |

Stop the legacy stack while keeping database volumes:

```bash
docker compose down
```

To reset the legacy stack completely, including Redis, Spark checkpoints,
PostGIS, Neo4j, and MinIO data (**destructive**):

```bash
docker compose down -v
docker compose up -d --build
```

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `permission denied ... /var/run/docker.sock` | Run `sudo usermod -aG docker "$USER"`, log out and back in, then rerun `docker ps`. |
| `port is already allocated` on `8000` | Stop the other stack with `docker compose -f docker-compose.v1.yml down` or `docker compose down`. |
| API health check fails | Run `docker compose logs --tail=200 api` for the active stack. |
| Spark processor restarts | Run `docker compose logs --tail=200 spark-processor`; verify Kafka and Spark master are `Up`. |
| Crawler restarts | Run `docker compose logs --tail=200 crawler`; a successful finite crawl should finish as `Exited (0)`. |

For infrastructure-specific notes, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Kubernetes

Legacy Kubernetes manifests are in `k8s/base/`:

```bash
kubectl apply -f k8s/base/
```
