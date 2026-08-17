# PySpark 3.5.x supports Python through 3.11.  Keep the runtime on a supported
# version so the driver used by spark-processor matches the Spark 3.5 cluster.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc curl default-jre libxml2-dev libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "services.processing.worker_service.alert_worker"]
