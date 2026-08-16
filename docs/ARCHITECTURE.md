# معماری نهایی

ChatGPT مغز و تولیدکننده Plan است. GitHub-Autonomous-Agent Executor/CI است. AI-Agent-Manager Orchestrator و Security Gate است.

ChatGPT → chat_requests → GitHub Actions → AI-Agent-Manager → Build/Test/Security → Deploy

هیچ API مدل خارجی در این زنجیره استفاده نمی‌شود.

اگر تست یا Security Gate شکست بخورد، گزارش در Artifact ذخیره می‌شود و ChatGPT می‌تواند Plan اصلاحی بعدی را به همان صف ارسال کند.
