from fastapi import FastAPI, HTTPException
from services.shared.redis_client import ping_redis, get_redis_client
from services.shared.redis_metrics import RedisMetrics
from services.shared.redis_queue import RedisQueue

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

@app.get("/stats")
async def get_stats():
    return {
        "metrics": metrics.get_all_metrics(),
        "queue_length": raw_items_queue.length()
    }

@app.post("/items/test")
async def push_test_item(title: str, url: str):
    item = {
        "title": title,
        "url": url,
        "source": "api_test"
    }
    raw_items_queue.push(item)
    metrics.increment("api_test_items")
    return {"message": "Item pushed to queue", "item": item}
