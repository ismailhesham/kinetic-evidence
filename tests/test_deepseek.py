import json
from unittest.mock import patch, MagicMock
from pipeline.llm import deepseek_client

def test_missing_key_returns_none(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert deepseek_client.analyze_script("Hello world.") is None