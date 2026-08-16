import json
import os
import pathlib
import subprocess
import sys
import traceback

MAX_OUTPUT = 20_000
MAX_COMMANDS = 8
ALLOWED_COMMAND_PREFIXES = ("python ", "python3 ", "pytest", "pip ", "pip3 ", "npm ", "npx ", "pnpm ", "yarn ", "node ", "ruff ", "mypy ", "eslint ", "tsc ", "vite")


def workspace() -> pathlib.Path:
    return pathlib.Path(os.getenv("AGENT_WORKSPACE", ".")).resolve()


def plan_path() -> pathlib.Path:
    return pathlib.Path(os.getenv("AGENT_PLAN", "agent/chatgpt_plan.json")).resolve()


def apply_files(root: pathlib.Path, files: list[dict]) -> int:
    applied = 0
    root = root.resolve()
    for item in files:
        if not isinstance(item, dict) or not item.get("path"):
            raise ValueError("هر فایل باید شامل path و content باشد.")
        relative = pathlib.PurePosixPath(str(item["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"مسیر غیرمجاز: {item['path']}")
        target = (root / pathlib.Path(*relative.parts)).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"مسیر خارج از پروژه: {item['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(item.get("content", "")), encoding="utf-8")
        applied += 1
    return applied


def run_command(root: pathlib.Path, command: str) -> tuple[int, str]:
    command = command.strip()
    if not command:
        return 0, "دستور خالی بود و نادیده گرفته شد."
    if not command.startswith(ALLOWED_COMMAND_PREFIXES):
        return 2, f"دستور غیرمجاز: {command}"
    try:
        result = subprocess.run(command, cwd=root, shell=True, text=True, capture_output=True, timeout=600, check=False)
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode, output[-MAX_OUTPUT:]
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + "\n" + (exc.stderr or "")).strip()
        return 124, (output + "\nخطا: زمان اجرای دستور تمام شد.")[-MAX_OUTPUT:]
    except Exception as exc:
        return 1, f"خطای اجرای دستور: {type(exc).__name__}: {exc}"


def load_plan(path: pathlib.Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"برنامه ChatGPT پیدا نشد: {path}")
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ValueError("فایل برنامه ChatGPT خالی است.")
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as exc:
        try:
            plan = json.loads(raw, strict=False)
        except json.JSONDecodeError:
            snippet = raw[max(0, exc.pos - 100):min(len(raw), exc.pos + 100)].replace("\n", "\\n")
            raise ValueError(f"JSON برنامه ChatGPT نامعتبر است: خط {exc.lineno} ستون {exc.colno}: {exc.msg}; اطراف خطا: {snippet}") from exc
    if not isinstance(plan, dict):
        raise ValueError("برنامه ChatGPT باید یک شیء JSON باشد.")
    files = plan.get("files", [])
    commands = plan.get("commands", [])
    if not isinstance(files, list) or not isinstance(commands, list):
        raise ValueError("files و commands باید آرایه باشند.")
    for index, item in enumerate(files):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("content", ""), str):
            raise ValueError(f"فایل شماره {index + 1} ساختار معتبری ندارد.")
    for index, command in enumerate(commands):
        if not isinstance(command, str):
            raise ValueError(f"دستور شماره {index + 1} باید رشته باشد.")
    return plan


def main() -> int:
    root = workspace()
    path = plan_path()
    result_path = pathlib.Path(os.getenv("AGENT_RESULT", "agent-result.json")).resolve()
    result = {"success": False, "summary": "", "tests": [], "source": "ChatGPT", "error": None, "workspace": str(root)}
    try:
        root.mkdir(parents=True, exist_ok=True)
        plan = load_plan(path)
        result["summary"] = plan.get("summary", "")
        files = plan.get("files", [])
        commands = plan.get("commands", [])[:MAX_COMMANDS]
        if not files and not commands and not plan.get("done", False):
            raise ValueError("برنامه ChatGPT خالی است. ابتدا باید files یا commands تولید شوند.")
        result["files_applied"] = apply_files(root, files)
        for command in commands:
            code, output = run_command(root, command)
            result["tests"].append({"command": command, "code": code, "output": output})
            print(f"$ {command}\n{output}", flush=True)
            if code != 0:
                break
        result["success"] = not any(item["code"] != 0 for item in result["tests"]) and bool(plan.get("done", False))
        if not result["success"]:
            result["error"] = "برنامه کامل نشده یا یکی از تست‌ها شکست خورده است."
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        print("خطای Executor:", result["error"], file=sys.stderr)
        traceback.print_exc()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("گزارش Executor:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
