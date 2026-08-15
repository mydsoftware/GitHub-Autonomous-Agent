import json
import os
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
    """درخواست ساخت یا اصلاح پروژه را از GitHub Models دریافت می‌کند."""
    token = os.environ["GITHUB_TOKEN"]
    model = os.getenv("AI_MODEL", "openai/gpt-4.1")

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
        "https://models.github.ai/inference/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        data = json.loads(response.read().decode("utf-8"))

    text = data["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
