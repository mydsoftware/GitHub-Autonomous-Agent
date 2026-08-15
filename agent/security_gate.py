from __future__ import annotations

import json
import os
import pathlib
import sys

MANAGER_ROOT = pathlib.Path(os.getenv("AI_MANAGER_ROOT", "ai-agent-manager")).resolve()
sys.path.insert(0, str(MANAGER_ROOT))
from agents.security_agent import SecurityAgent  # noqa: E402


def source_text(root: pathlib.Path) -> str:
    chunks = []
    ignored = {".git", "node_modules", ".venv", "venv", "__pycache__"}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        if path.suffix.lower() not in {".html", ".htm", ".css", ".js", ".ts", ".py", ".php", ".json", ".yml", ".yaml"}:
            continue
        try:
            chunks.append(f"\n--- {path.relative_to(root)} ---\n{path.read_text(encoding='utf-8', errors='ignore')}")
        except OSError:
            pass
    return "".join(chunks)


def main() -> int:
    root = pathlib.Path(os.getenv("AGENT_WORKSPACE", ".")).resolve()
    result = SecurityAgent().scan_source(source_text(root))
    output = {
        "passed": result.passed,
        "findings": [
            {"severity": f.severity, "category": f.category, "message": f.message}
            for f in result.findings
        ],
    }
    pathlib.Path("security-result.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
