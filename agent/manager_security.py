from __future__ import annotations

import json
import os
import pathlib
import sys
import uuid


MANAGER_ROOT = pathlib.Path(os.environ.get("AI_MANAGER_ROOT", "ai-agent-manager")).resolve()


def collect_source(root: pathlib.Path) -> str:
    ignored = {".git", ".venv", "node_modules", "__pycache__", "agent-results", "site.zip"}
    extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".php", ".json", ".yml", ".yaml", ".env"}
    chunks: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        if path.suffix.lower() not in extensions and path.name not in {"Dockerfile", "docker-compose.yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if len(text) > 200_000:
            text = text[:200_000]
        chunks.append(f"\n--- {path.relative_to(root)} ---\n{text}")
    return "".join(chunks)


def main() -> int:
    if not MANAGER_ROOT.is_dir():
        raise RuntimeError(f"AI-Agent-Manager پیدا نشد: {MANAGER_ROOT}")
    sys.path.insert(0, str(MANAGER_ROOT))
    from agents.security_agent import SecurityAgent
    from manager.task import Task

    project_root = pathlib.Path(".").resolve()
    source = collect_source(project_root)
    task = Task(
        id=f"security-{uuid.uuid4().hex[:8]}",
        title="Security scan",
        description=json.dumps({"action": "source", "source": source}, ensure_ascii=False),
        agent="security",
    )
    raw = SecurityAgent().run(task)
    result = json.loads(raw)
    pathlib.Path("security-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
