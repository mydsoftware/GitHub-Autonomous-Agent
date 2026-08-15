import json
import pathlib
import shlex
import subprocess
import sys
import traceback

MAX_OUTPUT = 20_000
MAX_COMMANDS = 8
ALLOWED_COMMAND_PREFIXES = (
    "python ", "python3 ", "pytest", "pip ", "pip3 ", "npm ", "npx ",
    "pnpm ", "yarn ", "node ", "ruff ", "mypy ", "eslint ", "tsc ", "vite",
)


def apply_files(root: pathlib.Path, files: list[dict]) -> int:
    """فایل‌های تولیدشده توسط ChatGPT را با اعتبارسنجی مسیر در مخزن ایجاد می‌کند."""
    applied = 0
    for item in files:
        if not isinstance(item, dict) or not item.get("path"):
            raise ValueError("هر فایل باید شامل path و content باشد.")
        relative = pathlib.PurePosixPath(str(item["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"مسیر غیرمجاز: {item['path']}")
        target = (root / pathlib.Path(*relative.parts)).resolve()
        if root.resolve() != target and root.resolve() not in target.parents:
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
        result = subprocess.run(
            command,
            cwd=root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
        )
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
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON برنامه ChatGPT نامعتبر است: خط {exc.lineno} ستون {exc.colno}: {exc.msg}") from exc
    if not isinstance(plan, dict):
        raise ValueError("برنامه ChatGPT باید یک شیء JSON باشد.")
    if not isinstance(plan.get("files", []), list):
        raise ValueError("فیلد files باید آرایه باشد.")
    if not isinstance(plan.get("commands", []), list):
        raise ValueError("فیلد commands باید آرایه باشد.")
    return plan


def main() -> int:
    root = pathlib.Path(".").resolve()
    plan_path = root / "agent" / "chatgpt_plan.json"
    result_path = root / "agent-result.json"
    result = {"success": False, "summary": "", "tests": [], "source": "ChatGPT", "error": None}

    try:
        plan = load_plan(plan_path)
        result["summary"] = plan.get("summary", "")
        files = plan.get("files", [])
        commands = plan.get("commands", [])[:MAX_COMMANDS]

        if not files and not commands and not plan.get("done", False):
            raise ValueError(
                "برنامه ChatGPT خالی است. ابتدا ChatGPT باید files/commands را تولید کند و سپس Executor اجرا شود."
            )

        applied = apply_files(root, files)
        result["files_applied"] = applied

        for command in commands:
            code, output = run_command(root, str(command))
            test = {"command": command, "code": code, "output": output}
            result["tests"].append(test)
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

    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("گزارش Executor:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
