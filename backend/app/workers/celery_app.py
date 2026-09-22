import os
from celery import Celery

celery_app = Celery("trinetra_layer2", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"), backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
