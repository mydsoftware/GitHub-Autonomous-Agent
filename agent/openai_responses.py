import json
import os
import urllib.error
import urllib.request


SYSTEM_PROMPT = """
تو هسته هوش مصنوعی یک عامل مهندسی نرم‌افزار خودمختار هستی.
تمام پاسخ‌ها، توضیحات و کامنت‌های تولیدی باید فارسی باشند.
وظیفه تو دریافت درخواست کاربر، طراحی، پیاده‌سازی، تست، اصلاح و تکمیل پروژه است.
هر بار فقط یک JSON معتبر برگردان و هیچ متن دیگری خارج از JSON ننویس.
ساختار JSON دقیقاً این باشد:
{
  "summary": "خلاصه فارسی کار",
  "files": [{"path": "مسیر فایل", "content": "محتوای کامل فایل"}],
  "commands": ["دستورهای مجاز برای تست یا ساخت"],
  "done": true
}

قواعد:
- فقط فایل‌های لازم را تغییر بده.
- مسیر فایل‌ها باید نسبی و داخل مخزن باشند.
- برای درخواست‌های ساخت سایت، یک سایت کامل و قابل اجرا بساز و فایل انتشار اصلی را در `site/index.html` قرار بده.
- برای سایت‌های ساده از HTML/CSS/JavaScript بدون وابستگی غیرضروری استفاده کن.
- اگر پروژه به Build نیاز دارد، فایل‌های پیکربندی و اسکریپت‌های لازم را هم ایجاد کن.
- دستورات فقط برای نصب وابستگی، تست، lint، build یا ابزارهای توسعه باشند.
- از دستورهای مخرب، حذف گسترده فایل‌ها، دسترسی به secrets یا تغییر تنظیمات امنیتی خودداری کن.
- قبل از اعلام done، تست یا build مناسب را اجرا کن.
- اگر تست شکست خورد، در دور بعد بر اساس بازخورد آن را اصلاح کن.
""".strip()

GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"


def _request_github_models(token: str, model: str, prompt: str) -> dict:
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")
    request = urllib.request.Request(
        GITHUB_MODELS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_openai(base_url: str, api_key: str, model: str, prompt: str) -> dict:
    payload = json.dumps({
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": prompt,
        "store": False,
    }).encode("utf-8")
    request = urllib.request.Request(
        base_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_text(data: dict, github_models: bool = False) -> str:
    if github_models:
        choices = data.get("choices", [])
        if choices:
            return (choices[0].get("message", {}).get("content") or "").strip()
        return ""

    text = data.get("output_text", "").strip()
    if text:
        return text
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text += content.get("text", "")
    return text.strip()


def _parse_model_result(text: str) -> dict:
    if not text:
        raise RuntimeError("مدل پاسخ متنی قابل استفاده‌ای برنگرداند.")
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def ask_model(task: str, context: str, feedback: str = "") -> dict:
    """ابتدا از GitHub Models با GITHUB_TOKEN استفاده می‌کند و سپس Providerهای جایگزین را امتحان می‌کند."""
    prompt = f"""
درخواست کاربر:
{task}

ساختار فعلی پروژه:
{context}

بازخورد آخرین تست:
{feedback or 'هنوز تستی انجام نشده است.'}

بر اساس این اطلاعات، فایل‌های لازم را تولید یا اصلاح کن.
""".strip()

    providers = [
        (
            "GitHub Models",
            os.environ.get("GITHUB_TOKEN", ""),
            os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4.1"),
        ),
    ]

    last_error = None
    for name, token, model in providers:
        if not token or not model:
            continue
        try:
            data = _request_github_models(token, model, prompt)
            return _parse_model_result(_extract_text(data, github_models=True))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"خطای {name} ({exc.code}): {body[:2000]}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = RuntimeError(f"خطای ارتباط یا پاسخ {name}: {exc}")

    fallback = (
        os.environ.get("AI_FALLBACK_API_KEY", ""),
        os.getenv("AI_FALLBACK_BASE_URL", ""),
        os.getenv("AI_FALLBACK_MODEL", ""),
    )
    if all(fallback):
        try:
            data = _request_openai(fallback[1], fallback[0], fallback[2], prompt)
            return _parse_model_result(_extract_text(data))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"خطای Provider جایگزین ({exc.code}): {body[:2000]}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = RuntimeError(f"خطای ارتباط یا پاسخ Provider جایگزین: {exc}")

    raise last_error or RuntimeError("هیچ Provider فعالی برای مدل تنظیم نشده است.")
