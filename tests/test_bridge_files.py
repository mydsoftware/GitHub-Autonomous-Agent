from pathlib import Path


def test_example_request_exists():
    path = Path("chat_requests/example.json")
    assert path.is_file()
