import json
import pathlib
import subprocess
import sys

MAX_OUTPUT = 20_000
ALLOWED_COMMAND_PREFIXES = (
    "python ", "python3 ", "pytest", "pip ", "pip3 ", "npm ", "npx ",
    "pnpm ", "yarn ", "node ", "ruff ", "mypy ", "eslint ", "tsc ", "vite ",
)


def apply_files(root: pathlib.Path, files: list[dict]) -> None:
    """برنامه تولیدشده توسط ChatGPT را به فایل‌های مخزن تبدیل می‌کند."""
    for item in files:
        relative = pathlib.PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"مسیر غیرمجاز: {item['path']}")
        target = (root / pathlib.Path(*relative.parts)).resolve()
        if root.resolve() not in target.parents:
            raise ValueError(f"مسیر خارج از پروژه: {item['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")


def run_command(root: pathlib.Path, command: str) -> tuple[int, str]:
    command = command.strip()
    if not command or not command.startswith(ALLOWED_COMMAND_PREFIXES):
        return 2, f"دستور غیرمجاز: {command}"
    result = subprocess.run(command, cwd=root, shell=True, text=True, capture_output=True, timeout=600)
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode, output[-MAX_OUTPUT:]


def main() -> int:
    plan_path = pathlib.Path("agent/chatgpt_plan.json")
    if not plan_path.exists():
        print("خطا: برنامه ChatGPT پیدا نشد.")
        return 2
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    root = pathlib.Path(".").resolve()
    apply_files(root, plan.get("files", []))
    results = []
    for command in plan.get("commands", [])[:8]:
        code, output = run_command(root, command)
        results.append({"command": command, "code": code, "output": output})
        print(f"$ {command}\n{output}")
        if code != 0:
            break
    success = not any(item["code"] != 0 for item in results) and bool(plan.get("done", False))
    result = {
        "success": success,
        "summary": plan.get("summary", ""),
        "tests": results,
        "source": "ChatGPT",
    }
    pathlib.Path("agent-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
