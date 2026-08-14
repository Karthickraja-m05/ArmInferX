"""Unit tests for ArmServe AI Inference Engine and OpenAI API Router."""

from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.inference_engine import (
    ChatCompletionRequest,
    ChatMessage,
    CompletionRequest,
    engine,
)

client = TestClient(app)


def test_inference_engine_chat_completion():
    """Verify inference engine generates valid chat completion responses."""
    req = ChatCompletionRequest(
        model="qwen2.5-0.5b-instruct",
        messages=[
            ChatMessage(role="user", content="Hello ArmServe! Tell me about ARM64 execution.")
        ],
        temperature=0.7,
        max_tokens=100,
    )
    res = engine.generate_chat_completion(req)
    assert res["object"] == "chat.completion"
    assert res["model"] == "qwen2.5-0.5b-instruct"
    assert len(res["choices"]) > 0
    assert "ARM64" in res["choices"][0]["message"]["content"]
    assert res["usage"]["prompt_tokens"] > 0
    assert res["usage"]["completion_tokens"] > 0


def test_inference_engine_text_completion():
    """Verify inference engine generates text completions."""
    req = CompletionRequest(
        model="qwen2.5-0.5b-instruct",
        prompt="ArmServe benchmark latency is",
        max_tokens=50,
    )
    res = engine.generate_completion(req)
    assert res["object"] == "text_completion"
    assert len(res["choices"]) > 0
    assert res["usage"]["total_tokens"] > 0


def test_openai_api_list_models_endpoint():
    """Test GET /v1/models endpoint."""
    response = client.get("/v1/models")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    model_ids = [m["id"] for m in data["data"]]
    assert "qwen2.5-0.5b-instruct" in model_ids


def test_openai_api_chat_completions_endpoint():
    """Test POST /v1/chat/completions endpoint."""
    payload = {
        "model": "qwen2.5-0.5b-instruct",
        "messages": [
            {"role": "user", "content": "Explain sub-millisecond p99 benchmark optimization."}
        ],
        "temperature": 0.5,
        "max_tokens": 128,
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == status.HTTP_200_OK
    res = response.json()
    assert res["object"] == "chat.completion"
    assert "choices" in res
    assert res["choices"][0]["message"]["role"] == "assistant"
