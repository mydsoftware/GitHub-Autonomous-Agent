import json
import os
import urllib.error
import urllib.request


SYSTEM_PROMPT = """
تو هسته هوش مصنوعی یک عامل مهندسی نرم‌افزار خودمختار هستی.
تمام پاسخ‌ها و توضیحاتت فارسی باشند.
وظیفه تو طراحی و پیاده‌سازی نرم‌افزار بر اساس درخواست کاربر است.
هر بار فقط یک JSON معتبر برگردان و هیچ متن دیگری خارج از JSON ننویس.
ساختار JSON دقیقاً این باشد:
{
  "summary": "خلاصه فارسی کار",
  "files": [
    {"path": "مسیر فایل", "content": "محتوای کامل فایل"}
  ],
  "commands": ["دستورهای مجاز برای تست یا ساخت"],
  "done": true
}
فقط فایل‌هایی را تغییر بده که برای انجام درخواست لازم هستند.
دستورها فقط برای نصب وابستگی، تست، lint، build یا اجرای ابزارهای توسعه باشند.
از دستورهای مخرب، حذف گسترده فایل‌ها، دسترسی به secrets یا تغییر تنظیمات امنیتی خودداری کن.
""".strip()


def ask_model(task: str, context: str, feedback: str = "") -> dict:
    """درخواست ساخت یا اصلاح پروژه را از ارائه‌دهنده مدل دریافت می‌کند."""
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("AI_MODEL", "gpt-5-mini")
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1/chat/completions")

    prompt = f"""
درخواست کاربر:
{task}

ساختار فعلی پروژه:
{context}

بازخورد آخرین تست:
{feedback or 'هنوز تستی انجام نشده است.'}

بر اساس این اطلاعات، فایل‌های لازم را تولید یا اصلاح کن.
""".strip()

    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")

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

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"خطای API مدل ({exc.code}): {body[:2000]}") from exc

    text = data["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
