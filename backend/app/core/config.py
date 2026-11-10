from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCRIBBLE_", env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    chunk_size: int = 64 * 1024
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def recordings_dir(self) -> Path:
        return self.data_dir / "recordings"

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "recordings.json"


settings = Settings()
