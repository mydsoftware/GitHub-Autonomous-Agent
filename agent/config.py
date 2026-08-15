from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """تنظیمات اصلی عامل خودمختار."""

    ai_provider: str = os.getenv("AI_PROVIDER", "github_models")
    model: str = os.getenv("AI_MODEL", "openai/gpt-4.1")
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "8"))
    workspace: str = os.getenv("AGENT_WORKSPACE", ".")


settings = Settings()
