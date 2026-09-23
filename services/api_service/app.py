from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from services.storage.shared.redis_client import ping_redis, get_redis_client
from services.storage.shared.redis_metrics import RedisMetrics
from services.storage.shared.redis_queue import RedisQueue
from services.storage.shared.url_frontier import UrlFrontier
from services.storage.common.security import is_safe_url
import os

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(
    header_key: str = Security(api_key_header),
):
    expected_key = os.getenv("API_KEY", "trinetra-dev-secret")
    if header_key == expected_key:
        return header_key
    raise HTTPException(
        status_code=403,
        detail="Could not validate credentials",
    )

app = FastAPI(title="Trinetra OSINT API")
metrics = RedisMetrics()
raw_items_queue = RedisQueue("raw_items")

@app.get("/")
async def root():
    return {
        "status": "online",
        "redis_connected": ping_redis(),
        "message": "Welcome to Trinetra OSINT API"
    }

@app.get("/health")
async def health_check():
    if not ping_redis():
        raise HTTPException(status_code=503, detail="Redis connection failed")
    return {"status": "healthy", "redis": "connected"}

@app.get("/stats", dependencies=[Depends(get_api_key)])
async def get_stats():
    frontier = UrlFrontier(metrics=metrics)
    return {
        "metrics": metrics.get_all_metrics(),
        "queue_length": raw_items_queue.length(),
        "frontier": frontier.stats(),
    }

@app.get("/frontier/stats", dependencies=[Depends(get_api_key)])
async def get_frontier_stats():
    frontier = UrlFrontier(metrics=metrics)
    return frontier.stats()

@app.get("/frontier/dead-letters", dependencies=[Depends(get_api_key)])
async def get_frontier_dead_letters(limit: int = 20):
    # Bound the limit to prevent DoS
    safe_limit = max(1, min(limit, 100))
    frontier = UrlFrontier(metrics=metrics)
    return {
        "dead_letter_length": frontier.dead_letter_length(),
        "items": frontier.get_dead_letters(limit=safe_limit),
    }

@app.post("/items/test", dependencies=[Depends(get_api_key)])
async def push_test_item(title: str, url: str):
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Insecure or invalid URL")
    
    item = {
        "title": title[:200], # Basic title bounding
        "url": url,
        "source": "api_test"
    }
    raw_items_queue.push(item)
    metrics.increment("api_test_items")
    return {"message": "Item pushed to queue", "item": item}
