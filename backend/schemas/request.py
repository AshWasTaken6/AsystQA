import re

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    code: str = Field(
        ...,
        min_length=1,
        max_length=50000,  # 50KB max code size
        description="Source code to analyze.",
    )
    language: str = Field(..., min_length=1, description="Programming language of the source.")
    filename: str | None = Field(default=None, max_length=255, description="Optional source filename.")

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = value.strip().lower()
        # Allowed languages for analysis
        allowed = {
            "c",
            "cpp",
            "csharp",
            "css",
            "go",
            "html",
            "java",
            "javascript",
            "php",
            "python",
            "rust",
            "typescript",
        }
        if normalized not in allowed:
            allowed_list = ", ".join(sorted(allowed))
            raise ValueError(f"Unsupported language '{value}'. Allowed: {allowed_list}")
        return normalized

    @field_validator("filename")
    @classmethod
    def sanitize_filename(cls, value: str | None) -> str | None:
        if value is None:
            return value

        sanitized = re.sub(r"[^A-Za-z0-9._ -]", "_", value).strip()
        return sanitized or None
