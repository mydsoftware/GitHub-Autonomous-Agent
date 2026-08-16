import json


def test_chat_request_contract():
    plan = {
        "done": True,
        "summary": "demo",
        "files": [{"path": "site/index.html", "content": "<h1>Demo</h1>"}],
        "commands": ["python -m pytest -q"],
    }
    assert isinstance(plan["done"], bool)
    assert isinstance(plan["files"], list)
    assert all(isinstance(item["path"], str) for item in plan["files"])
    assert isinstance(plan["commands"], list)
    assert json.loads(json.dumps(plan))["summary"] == "demo"
