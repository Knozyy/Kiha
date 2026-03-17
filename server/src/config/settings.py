"""Kiha Server — Merkezi Konfigürasyon."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class KihaSettings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="KIHA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    debug: bool = False

    # Database (PostgreSQL)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "kiha"
    db_user: str = "kiha_user"
    db_password: str = ""

    # Cache (Redis)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    # Authentication (JWT)
    jwt_secret: str = ""
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Security
    api_secret: str = ""
    dtls_psk: str = ""

    # AI Inference
    model_path: str = "./models/yolov8n.onnx"
    inference_device: str = "cuda"

    # VLM (Vision Language Model)
    gemini_api_key: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llava:7b"

    # UDP Receiver
    udp_host: str = "0.0.0.0"
    udp_port: int = 9000

    # WebSocket
    ws_port: int = 8001

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/0"


def get_settings() -> KihaSettings:
    """Return a cached settings instance."""
    return KihaSettings()
