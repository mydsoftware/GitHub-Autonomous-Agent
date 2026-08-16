#!/usr/bin/env python3
"""بررسی امنیتی مستقل و فارسی برای اجرای عامل خودکار."""
from __future__ import annotations

import json
import pathlib
import re
import sys

PATTERNS = (
    (r"eval\s*\(", "high", "اجرای کد", "استفاده از eval شناسایی شد."),
    (r"exec\s*\(", "high", "اجرای کد", "استفاده از exec شناسایی شد."),
    (r"(?:password|api[_-]?key|secret|token)\s*=\s*['\"]", "critical", "راز", "احتمال hard-code شدن Secret شناسایی شد."),
    (r"verify\s*=\s*False", "high", "TLS", "غیرفعال کردن بررسی TLS شناسایی شد."),
    (r"\b(?:shell_exec|system|passthru)\s*\(", "high", "اجرای فرمان", "اجرای مستقیم فرمان سیستم شناسایی شد."),
    (r"pickle\.loads\s*\(", "high", "Deserialization", "Deserialization ناامن شناسایی شد."),
)


def main() -> int:
    root = pathlib.Path(".").resolve()
    findings: list[dict[str, str]] = []
    extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".html", ".css", ".json", ".yml", ".yaml", ".sh"}
    ignored = {".git", "node_modules", ".venv", "venv", "__pycache__"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions or any(part in ignored for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, severity, category, message in PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                findings.append({"file": str(path.relative_to(root)), "severity": severity, "category": category, "message": message})

    result = {"status": "failed" if any(f["severity"] in {"critical", "high"} for f in findings) else "passed", "findings": findings}
    pathlib.Path("security-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
