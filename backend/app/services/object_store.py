import os
from io import BytesIO
from pathlib import Path
from backend.app.security.http_client import sha256

class ObjectStore:
    """Content-addressed local fallback; set MINIO_ENDPOINT for the production backend."""
    def __init__(self, root: str | None = None):
        self.root = Path(root or os.getenv("RAW_OBJECT_ROOT", "/tmp/trinetra-raw-evidence")); self.endpoint = os.getenv("MINIO_ENDPOINT")
        self.client = None
        if self.endpoint:
            from minio import Minio
            self.client = Minio(self.endpoint, access_key=os.getenv("MINIO_ACCESS_KEY", "trinetra"), secret_key=os.getenv("MINIO_SECRET_KEY", "change-me"), secure=os.getenv("MINIO_SECURE", "false").lower() == "true")
    def put(self, data: bytes, sha: str | None = None) -> str:
        sha = sha or sha256(data)
        if self.client:
            bucket = os.getenv("MINIO_BUCKET_RAW", "raw-evidence")
            if not self.client.bucket_exists(bucket): self.client.make_bucket(bucket)
            key = f"raw/{sha[:2]}/{sha}"; self.client.put_object(bucket, key, BytesIO(data), len(data), content_type="application/octet-stream"); return f"s3://{bucket}/{key}"
        path = self.root / sha[:2] / sha; path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists(): path.write_bytes(data)
        return f"file://{path}"
