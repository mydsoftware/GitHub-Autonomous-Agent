# پل ChatGPT → AI-Agent-Manager

ChatGPT درخواست را به Plan JSON تبدیل می‌کند و از طریق اتصال GitHub آن را در `chat_requests/` قرار می‌دهد. GitHub Actions درخواست را اجرا می‌کند.

## قرارداد

```json
{
  "done": true,
  "summary": "ساخت سایت فروشگاهی",
  "files": [
    {"path": "site/index.html", "content": "..."},
    {"path": "site/style.css", "content": "..."}
  ],
  "commands": ["python -m pytest -q"]
}
```

## نقش‌ها

- ChatGPT: مغز، Planner و تولیدکننده/اصلاح‌کننده Plan
- GitHub-Autonomous-Agent: Executor، CI و Deploy
- AI-Agent-Manager: Orchestrator و Security Gate
- GH_PAT: دسترسی Cross-Repository به AI-Agent-Manager

هیچ API مدل خارجی استفاده نمی‌شود.
