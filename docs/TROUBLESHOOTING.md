# Troubleshooting Guide: Infrastructure

This document tracks common issues and resolutions for the Trinetra collection and pipeline infrastructure.

## 1. Connectivity Issues

### Redis
- **Symptom:** `ConnectionError` when accessing cache or queue.
- **Resolution:** Verify `redis` service is healthy in `docker-compose.yml`. Ensure `REDIS_URL` in `.env` is `redis://redis:6379/0` when running within docker, or `redis://localhost:6380/0` from the host.

### Kafka
- **Symptom:** `NoBrokersAvailable` or producer/consumer hangs.
- **Resolution:** Ensure `zookeeper` and `kafka` services are running. Check `KAFKA_BOOTSTRAP_SERVERS`. If running locally, you might need to use the `PLAINTEXT_HOST` listener.

### MinIO
- **Symptom:** Unable to upload or access files.
- **Resolution:** Verify container `osint_minio` is running. Check `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` (currently `minioadmin`).

### PostGIS
- **Symptom:** `psycopg2.OperationalError: could not connect to server`.
- **Resolution:** Ensure `osint_postgis` is running. Check `POSTGRES_USER` and `POSTGRES_DB` settings. Verify container port `5432` is mapped correctly.

## 2. Scraping & Collection Issues

### Scrapy/Crawling
- **Symptom:** `ModuleNotFoundError: No module named 'scrapy'`.
- **Resolution:** Ensure the virtual environment is properly activated or running inside the Docker container. If local, `pip install -r requirements.txt`.

### Proxy/Browser
- **Symptom:** `SCRAPLING_BROWSER_ENABLED is false` or timeouts.
- **Resolution:** Check `.env` configuration. For dynamic/stealth crawling, ensure browser environment dependencies are met.

## 3. Geographic Pipeline

### Geocoding
- **Symptom:** Geocoder returns no results or fails.
- **Resolution:** Validate that NER output contains valid place names. If using `geopy` with an API, ensure rate limits are respected.

### PostGIS Spatial
- **Symptom:** Spatial query errors.
- **Resolution:** Ensure the `postgis` extension is enabled in the database (`CREATE EXTENSION IF NOT EXISTS postgis;`).
