import json
from pathlib import Path


def test_chat_request_contract():
    plan = json.loads(Path("chat_requests/example.json").read_text(encoding="utf-8"))
    assert plan["done"] is True
    assert isinstance(plan["summary"], str)
    assert isinstance(plan["files"], list)
    assert all(isinstance(item.get("path"), str) and isinstance(item.get("content"), str) for item in plan["files"])
    assert isinstance(plan["commands"], list)
    assert all(isinstance(command, str) for command in plan["commands"])
