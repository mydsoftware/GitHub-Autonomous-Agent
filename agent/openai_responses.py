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


def ask_model(task: str, context: str, feedback: str = "") -> dict:
    """درخواست ساخت یا اصلاح پروژه را از OpenAI Responses API دریافت می‌کند."""
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("AI_MODEL", "gpt-5.6")
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1/responses")
    prompt = f"""
درخواست کاربر:
{task}

ساختار فعلی پروژه:
{context}

بازخورد آخرین تست:
{feedback or 'هنوز تستی انجام نشده است.'}

بر اساس این اطلاعات، فایل‌های لازم را تولید یا اصلاح کن.
""".strip()
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
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"خطای API مدل ({exc.code}): {body[:2000]}") from exc

    text = data.get("output_text", "").strip()
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text += content.get("text", "")
        text = text.strip()
    if not text:
        raise RuntimeError("مدل پاسخ متنی قابل استفاده‌ای برنگرداند.")
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
