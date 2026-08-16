# ChatGPT Bridge

## جریان واقعی

1. ChatGPT درخواست کاربر را به **Plan JSON** تبدیل می‌کند.
2. ChatGPT همان Plan را در `chat_requests/<id>.json` در این Repository ثبت می‌کند.
3. Push به `chat_requests/*.json` Workflow را اجرا می‌کند.
4. Workflow Plan را اجرا می‌کند.
5. AI-Agent-Manager به‌عنوان Orchestrator/Security Gate استفاده می‌شود.
6. در صورت عبور از Gateها، Deploy انجام می‌شود.
7. گزارش در Artifact و `agent-results/` ثبت می‌شود.

## قرارداد Plan

```json
{
  "done": true,
  "summary": "ساخت سایت فروشگاهی",
  "files": [
    {"path": "site/index.html", "content": "..."}
  ],
  "commands": ["python -m pytest -q"]
}
```

**نکته:** هیچ مدل خارجی در Workflow استفاده نمی‌شود. مدل/مغز فقط ChatGPT است. اگر تست یا Security Gate شکست بخورد، Workflow گزارش را ثبت می‌کند تا ChatGPT بر اساس آن Plan اصلاحی جدید را در صف قرار دهد.
