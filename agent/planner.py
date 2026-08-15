import json
import os
import pathlib


def load_chatgpt_plan(task: str) -> dict:
    """Plan تولیدشده توسط خود ChatGPT را از ورودی Workflow می‌خواند."""
    text = task.strip()
    if "```" in text:
        text = text.replace("```json", "").replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("ورودی باید Plan JSON تولیدشده توسط ChatGPT باشد.")
    plan = json.loads(text[start:end + 1])
    if not isinstance(plan, dict):
        raise ValueError("Plan باید یک شیء JSON باشد.")
    plan.setdefault("summary", "")
    plan.setdefault("files", [])
    plan.setdefault("commands", [])
    plan["done"] = bool(plan.get("done", True))
    if not isinstance(plan["files"], list) or not isinstance(plan["commands"], list):
        raise ValueError("files و commands باید آرایه باشند.")
    for item in plan["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("content", ""), str):
            raise ValueError("ساختار فایل در Plan معتبر نیست.")
    for command in plan["commands"]:
        if not isinstance(command, str):
            raise ValueError("هر command باید رشته باشد.")
    return plan


def main() -> None:
    task = os.environ.get("AGENT_TASK", "").strip()
    if not task:
        raise RuntimeError("دستور/Plan ChatGPT خالی است.")
    plan = load_chatgpt_plan(task)
    pathlib.Path("agent/chatgpt_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "source": "ChatGPT conversation",
        "summary": plan.get("summary", ""),
        "files": len(plan.get("files", [])),
        "commands": len(plan.get("commands", [])),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
