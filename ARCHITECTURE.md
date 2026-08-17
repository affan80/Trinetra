# Infrastructure Overview

This project implements the architecture for scalable intelligence ingestion and analysis.

## Directory Structure
- `ingestion/`: Web, News, and PDF ingestion (scrapers, crawlers)
- `processing/`: Kafka consumer, Text extraction, NER, Entity Resolution, Graph extraction
- `storage/`: Clients for Neo4j, PostGIS, MinIO, Redis
- `analytics/`: Graph search, Path analysis, Correlation, AI Agent
- `api/`: API services for Analyst UI
- `k8s/`: Kubernetes manifests for production deployment
- `docs/`: Troubleshooting and architectural details

## Orchestration
- **Docker Compose:** Use for local development and integration testing.
- **Kubernetes:** Use for scalable production deployment (manifests in `k8s/`).

To run locally:
`docker-compose up -d`
