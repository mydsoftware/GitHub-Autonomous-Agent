import json
import os
import pathlib
import urllib.error
import urllib.request

API_URL = "https://api.openai.com/v1/responses"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6").strip() or "gpt-5.6"


def call_openai(prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Secret به نام OPENAI_API_KEY در GitHub تنظیم نشده است.")
    body = json.dumps({"model": MODEL, "input": prompt}).encode("utf-8")
    request = urllib.request.Request(API_URL, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = data.get("output_text")
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in ("output_text", "text") and content.get("text"):
                    text = content["text"]
                    break
            if text: break
    if not text: raise RuntimeError("OpenAI پاسخ متنی قابل استفاده برنگرداند.")
    return text.strip()


def clean_json(text: str) -> dict:
    if "```" in text:
        text = text.replace("```json", "").replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start: raise ValueError("پاسخ مدل شامل JSON معتبر نبود.")
    plan = json.loads(text[start:end + 1])
    if not isinstance(plan, dict): raise ValueError("Plan باید یک شیء JSON باشد.")
    plan.setdefault("summary", "")
    plan.setdefault("files", [])
    plan.setdefault("commands", [])
    plan["done"] = bool(plan.get("done", True))
    if not isinstance(plan["files"], list) or not isinstance(plan["commands"], list):
        raise ValueError("files و commands باید آرایه باشند.")
    return plan


def main() -> None:
    task = os.environ.get("AGENT_TASK", "").strip()
    if not task: raise RuntimeError("دستور Agent خالی است.")
    feedback = os.environ.get("AGENT_FEEDBACK", "").strip()
    root = pathlib.Path(".").resolve()
    existing = [str(p.relative_to(root)) for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts and "site" not in p.parts][:250]
    prompt = f"""
تو موتور برنامه‌ریزی GitHub Autonomous Agent هستی.
دستور کاربر را به Plan اجرایی تبدیل کن.

دستور کاربر:
{task}

بازخورد آخرین تست/امنیت:
{feedback or "(بدون بازخورد)"}

فایل‌های فعلی:
{chr(10).join(existing) or "(مخزن خالی)"}

فقط JSON معتبر:
{{"summary":"خلاصه فارسی","files":[{{"path":"مسیر نسبی","content":"محتوای کامل"}}],"commands":["تست/Build"],"done":true}}

قوانین:
- خطاها و Security Findingهای بازخورد را در اولویت اصلاح کن.
- اصلاح حداقلی و امن انجام بده.
- مسیر نسبی و بدون .. باشد.
- سایت باید خروجی واقعی داشته باشد.
- commands فقط تست/Build باشند.
- حداکثر 8 command.
"""
    plan = clean_json(call_openai(prompt))
    pathlib.Path("agent/chatgpt_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
