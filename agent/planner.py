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
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(raw)
            message = error_data.get("error", {}).get("message") or raw
            error_type = error_data.get("error", {}).get("type", "")
            error_code = error_data.get("error", {}).get("code", "")
            details = " | ".join(x for x in [error_type, error_code] if x)
            if details:
                message = f"{message} ({details})"
        except json.JSONDecodeError:
            message = raw or str(exc)
        raise RuntimeError(f"درخواست OpenAI با مدل '{MODEL}' رد شد: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"اتصال به OpenAI برقرار نشد: {exc.reason}") from exc

    text = data.get("output_text")
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in ("output_text", "text") and content.get("text"):
                    text = content["text"]
                    break
            if text:
                break
    if not text:
        raise RuntimeError("OpenAI پاسخ متنی قابل استفاده برنگرداند.")
    return text.strip()


def clean_json(text: str) -> dict:
    if "```" in text:
        text = text.replace("```json", "").replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("پاسخ مدل شامل JSON معتبر نبود.")
    plan = json.loads(text[start:end + 1])
    if not isinstance(plan, dict):
        raise ValueError("Plan باید یک شیء JSON باشد.")
    plan.setdefault("summary", "")
    plan.setdefault("files", [])
    plan.setdefault("commands", [])
    plan["done"] = bool(plan.get("done", True))
    if not isinstance(plan["files"], list) or not isinstance(plan["commands"], list):
        raise ValueError("files و commands باید آرایه باشند.")
    return plan


def main() -> None:
    task = os.environ.get("AGENT_TASK", "").strip()
    if not task:
        raise RuntimeError("دستور Agent خالی است.")
    feedback = os.environ.get("AGENT_FEEDBACK", "").strip()
    root = pathlib.Path(".").resolve()
    existing = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.parts and "site" not in path.parts:
            existing.append(str(path.relative_to(root)))
    existing_text = "\n".join(existing[:250]) or "(مخزن فعلاً خالی است)"
    prompt = f"""
تو موتور برنامه‌ریزی GitHub Autonomous Agent هستی.
دستور کاربر را به یک Plan اجرایی تبدیل کن تا روی Runner لینوکس اجرا شود.

دستور کاربر:
{task}

بازخورد آخرین اجرای تست/امنیت:
{feedback or "(هنوز بازخوردی وجود ندارد)"}

فایل‌های فعلی مخزن:
{existing_text}

خروجی فقط JSON معتبر باشد و هیچ Markdown یا توضیح خارج از JSON نداشته باشد.
ساختار:
{{"summary":"خلاصه فارسی کار","files":[{{"path":"مسیر نسبی","content":"محتوای کامل فایل"}}],"commands":["دستورهای تست/Build لازم"],"done":true}}

قوانین:
- خطاها و یافته‌های امنیتی بازخورد را در اولویت اصلاح قرار بده.
- اگر Security Finding وجود دارد، فقط اصلاح حداقلی و امن انجام بده و قابلیت اصلی را حفظ کن.
- مسیرها نسبی باشند و از .. استفاده نکنند.
- برای سایت، فایل‌های واقعی و کامل تولید کن؛ نه placeholder.
- commands فقط تست و Build باشند.
- حداکثر 8 command تولید کن.
"""
    plan = clean_json(call_openai(prompt))
    pathlib.Path("agent/chatgpt_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"model": MODEL, "summary": plan.get("summary"), "files": len(plan.get("files", [])), "commands": len(plan.get("commands", []))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
