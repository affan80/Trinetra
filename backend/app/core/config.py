import os


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./trinetra.db")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-development")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")


settings = Settings()
