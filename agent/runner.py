import json
import os
import pathlib
import subprocess
import sys

from github_model import ask_model


MAX_CONTEXT_BYTES = 120_000
ALLOWED_COMMAND_PREFIXES = (
    "python ",
    "python3 ",
    "pytest",
    "pip ",
    "pip3 ",
    "npm ",
    "npx ",
    "pnpm ",
    "yarn ",
    "node ",
    "ruff ",
    "mypy ",
    "eslint ",
    "tsc ",
    "vite ",
)


def project_context(root: pathlib.Path) -> str:
    """متن فایل‌های پروژه را برای آگاهی مدل جمع‌آوری می‌کند."""
    chunks = []
    total = 0
    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}

    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        if path.stat().st_size > 30_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        item = f"\n--- {path.relative_to(root)} ---\n{content}"
        if total + len(item.encode("utf-8")) > MAX_CONTEXT_BYTES:
            break
        chunks.append(item)
        total += len(item.encode("utf-8"))
    return "".join(chunks) or "پروژه هنوز فایل قابل خواندن ندارد."


def apply_files(root: pathlib.Path, files: list[dict]) -> None:
    """فایل‌های خروجی مدل را با جلوگیری از خروج از پوشه پروژه ذخیره می‌کند."""
    for item in files:
        relative = pathlib.PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"مسیر غیرمجاز: {item['path']}")
        target = (root / pathlib.Path(*relative.parts)).resolve()
        if root.resolve() not in target.parents and target != root.resolve():
            raise ValueError(f"مسیر خارج از پروژه: {item['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")


def run_command(root: pathlib.Path, command: str) -> tuple[int, str]:
    """یک دستور توسعه مجاز را اجرا می‌کند و خروجی آن را برمی‌گرداند."""
    command = command.strip()
    if not command or not command.startswith(ALLOWED_COMMAND_PREFIXES):
        return 2, f"دستور غیرمجاز: {command}"
    result = subprocess.run(
        command,
        cwd=root,
        shell=True,
        text=True,
        capture_output=True,
        timeout=600,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode, output[-20_000:]


def main() -> int:
    task = os.getenv("AGENT_TASK", "").strip()
    if not task:
        print("خطا: دستور عامل خالی است.")
        return 2

    root = pathlib.Path(os.getenv("AGENT_WORKSPACE", ".")).resolve()
    feedback = ""

    for iteration in range(1, int(os.getenv("MAX_ITERATIONS", "8")) + 1):
        print(f"\n=== دور مهندسی {iteration} ===")
        context = project_context(root)
        plan = ask_model(task, context, feedback)
        apply_files(root, plan.get("files", []))

        results = []
        commands = plan.get("commands", [])
        for command in commands[:8]:
            code, output = run_command(root, command)
            results.append({"command": command, "code": code, "output": output})
            print(f"$ {command}\n{output}")
            if code != 0:
                break

        failed = [item for item in results if item["code"] != 0]
        if not failed and plan.get("done", False):
            pathlib.Path("agent-result.json").write_text(
                json.dumps(
                    {
                        "success": True,
                        "iteration": iteration,
                        "summary": plan.get("summary", "کار با موفقیت انجام شد."),
                        "tests": results,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return 0

        feedback = json.dumps(results, ensure_ascii=False, indent=2)

    pathlib.Path("agent-result.json").write_text(
        json.dumps(
            {"success": False, "summary": "عامل به سقف تعداد دورهای مجاز رسید.", "feedback": feedback},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
