from dataclasses import dataclass, field
import os


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AsystQA Backend")
    api_prefix: str = os.getenv("API_PREFIX", "")
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        ]
    )


settings = Settings()
