# Intelligence Pipeline Infrastructure

A scalable, containerized architecture for intelligence ingestion, processing, and analysis.

## 🏗️ Architecture Overview

The system is modularly designed to handle high-volume data ingestion, processing, and graph-based analysis:

- **Ingestion:** Scrapers and crawlers (`services/ingestion/`).
- **Processing:** Data cleaning, extraction, and worker services (`services/processing/`).
- **Storage:** Clients for databases and file stores (`services/storage/`).
- **Analytics:** AI Agents and graph analysis (`services/analytics/`).
- **API:** Interface for Analyst UI (`services/api/`).

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose installed.

### 1. Configuration
1. Create a `.env` file in the root directory:
   ```bash
   cp example.env .env
   ```
2. Open `.env` and add your required API keys (NEVER commit this file):
   ```env
   BRAVE_SEARCH_API_KEY=your_key_here
   YOUTUBE_API_KEY=your_key_here
   ```

### 2. Running the Infrastructure
Start the entire software stack (API, workers, crawlers, databases, queues) with a single command:
```bash
jocker-compose up -d --build
```

### 3. Running Tests
To verify the system integrity using the test suite:
```bash
docker-compose run --rm api /usr/bin/python3 run_tests.sh
```

## 🛠️ Development & Management

- **API Service:** `http://localhost:8000`
- **MinIO Console:** `http://localhost:9001` (login: `minioadmin` / `minioadmin`)
- **Neo4j Browser:** `http://localhost:7474` (login: `neo4j` / `password`)
- **PostGIS:** Access via port `5432` (user: `osint_user` / `osint_password`)

## 📦 Kubernetes Deployment
Production manifests are located in the `k8s/` directory. Deploy using:
```bash
kubectl apply -f k8s/base/
```
