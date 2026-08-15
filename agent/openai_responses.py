import json
import os
import time
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
""".strip()

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"


def _request_openai(api_key: str, model: str, prompt: str) -> dict:
    payload = json.dumps({
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": prompt,
        "store": False,
    }).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
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


def _request_openai_compatible(base_url: str, api_key: str, model: str, prompt: str) -> dict:
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")
    request = urllib.request.Request(
        url,
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


def _request_github_models(token: str, model: str, prompt: str) -> dict:
    return _request_openai_compatible(GITHUB_MODELS_URL, token, model, prompt)


def _extract_text(data: dict, github_models: bool = False) -> str:
    if github_models or "choices" in data:
        choices = data.get("choices", [])
        if choices:
            return (choices[0].get("message", {}).get("content") or "").strip()
        return ""
    text = data.get("output_text", "").strip()
    if text:
        return text
    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "".join(parts).strip()


def _parse_model_result(text: str) -> dict:
    if not text:
        raise RuntimeError("مدل پاسخ متنی قابل استفاده‌ای برنگرداند.")
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def _github_models(model: str):
    configured = os.getenv("GITHUB_MODELS_MODELS", "")
    models = [m.strip() for m in configured.split(",") if m.strip()]
    if model and model not in models:
        models.insert(0, model)
    return models or ["openai/gpt-4.1", "openai/gpt-4o"]


def _retryable(code: int) -> bool:
    return code in (408, 409, 429, 500, 502, 503, 504)


def _describe_http_error(provider: str, exc: urllib.error.HTTPError) -> str:
    body = exc.read().decode("utf-8", errors="replace")
    return f"{provider} | HTTP {exc.code} | {body[:2000]}"


def ask_model(task: str, context: str, feedback: str = "") -> dict:
    prompt = f"""
درخواست کاربر:
{task}

ساختار فعلی پروژه:
{context}

بازخورد آخرین تست:
{feedback or 'هنوز تستی انجام نشده است.'}

بر اساس این اطلاعات، فایل‌های لازم را تولید یا اصلاح کن.
""".strip()

    errors = []

    # مدل اصلی: OpenAI API با کلید ذخیره‌شده در GitHub Secret.
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        model = os.getenv("OPENAI_MODEL", "gpt-5.6")
        for attempt in range(2):
            try:
                data = _request_openai(openai_key, model, prompt)
                return _parse_model_result(_extract_text(data))
            except urllib.error.HTTPError as exc:
                errors.append(_describe_http_error(f"OpenAI/{model}", exc))
                if _retryable(exc.code) and attempt == 0:
                    time.sleep(3)
                    continue
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                errors.append(f"OpenAI/{model} | {type(exc).__name__} | {exc}")
                break
    else:
        errors.append("OpenAI | OPENAI_API_KEY تنظیم نشده است")

    # Failover اول: GitHub Models.
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if github_token:
        for model in _github_models(os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4.1")):
            for attempt in range(2):
                try:
                    data = _request_github_models(github_token, model, prompt)
                    return _parse_model_result(_extract_text(data, github_models=True))
                except urllib.error.HTTPError as exc:
                    errors.append(_describe_http_error(f"GitHub Models/{model}", exc))
                    if _retryable(exc.code) and attempt == 0:
                        time.sleep(3)
                        continue
                    break
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                    errors.append(f"GitHub Models/{model} | {type(exc).__name__} | {exc}")
                    break
    else:
        errors.append("GitHub Models | GITHUB_TOKEN تنظیم نشده است")

    # Failover دوم: Provider سازگار با OpenAI، در صورت تنظیم Secretها.
    fallback_key = os.environ.get("AI_FALLBACK_API_KEY", "")
    fallback_url = os.environ.get("AI_FALLBACK_BASE_URL", "")
    fallback_model = os.environ.get("AI_FALLBACK_MODEL", "")
    if fallback_key and fallback_url and fallback_model:
        for attempt in range(2):
            try:
                data = _request_openai_compatible(fallback_url, fallback_key, fallback_model, prompt)
                return _parse_model_result(_extract_text(data))
            except urllib.error.HTTPError as exc:
                errors.append(_describe_http_error(f"Fallback/{fallback_model}", exc))
                if _retryable(exc.code) and attempt == 0:
                    time.sleep(3)
                    continue
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                errors.append(f"Fallback/{fallback_model} | {type(exc).__name__} | {exc}")
                break
    else:
        errors.append("Fallback | Secretهای Provider جایگزین کامل تنظیم نشده‌اند")

    raise RuntimeError("تمام Providerها شکست خوردند:\n" + "\n".join(f"- {error}" for error in errors))
