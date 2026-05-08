from dataclasses import dataclass, field
import os


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AsystQA Backend")
    api_prefix: str = os.getenv("API_PREFIX", "")
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]
    )


settings = Settings()
