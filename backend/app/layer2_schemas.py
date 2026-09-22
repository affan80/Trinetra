from pydantic import BaseModel, Field, field_validator
from backend.app.services.adapter_registry import supported

class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200); source_class: str; adapter_name: str; enabled: bool = True; allowed_domains: list[str] = []; config: dict = {}; rate_limit_per_minute: int = Field(default=30, ge=1, le=10000); cooldown_seconds: int = Field(default=0, ge=0)
    @field_validator("adapter_name")
    @classmethod
    def adapter_exists(cls, value):
        if not supported(value): raise ValueError("unsupported adapter")
        return value
class PlanCreate(BaseModel): profile_id: str; source_ids: list[str] = Field(min_length=1); interval_seconds: int = Field(default=900, ge=60, le=86400)
class WorkerHeartbeat(BaseModel): worker_name: str; adapter_names: list[str] = []
