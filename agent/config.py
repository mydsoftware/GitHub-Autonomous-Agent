from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    ai_provider: str = os.getenv("AI_PROVIDER", "openai")
    model: str = os.getenv("AI_MODEL", "gpt-5-mini")
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "8"))
    workspace: str = os.getenv("AGENT_WORKSPACE", ".")


settings = Settings()
