import json

import httpx
import pytest

from causalbridge.llm.client import ModelConfig, OllamaModel


def test_ollama_structured_output_and_generation_settings():
    seen = []

    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen2.5:3b",
                "done": True,
                "message": {"content": '{"ok":true}'},
                "prompt_eval_count": 12,
                "eval_count": 4,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        model = OllamaModel(ModelConfig(seed=42), client=client)
        generation = model.generate([{"role": "user", "content": "Query"}], {"type": "object"})
    assert generation.input_tokens == 12
    assert generation.output_tokens == 4
    assert seen[0]["stream"] is False
    assert seen[0]["format"] == {"type": "object"}
    assert seen[0]["options"]["seed"] == 42
    assert seen[0]["options"]["temperature"] == 0


@pytest.mark.parametrize("think", [None, False, True])
def test_ollama_thinking_is_sent_only_when_explicit(think):
    seen = []

    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"model": "qwen3:8b", "done": True, "message": {"content": "{}"}},
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        model = OllamaModel(ModelConfig(model="qwen3:8b", think=think), client=client)
        model.generate([], {})

    if think is None:
        assert "think" not in seen[0]
    else:
        assert seen[0]["think"] is think


@pytest.mark.parametrize("think", ["false", 0, 1])
def test_ollama_thinking_setting_requires_a_boolean(think):
    with pytest.raises(ValueError):
        ModelConfig(think=think)


@pytest.mark.parametrize(
    "response",
    [
        {"message": {}},
        {"message": {"content": "{}"}, "done": False},
        {"message": {"content": "{}"}, "done": True, "done_reason": "length"},
    ],
)
def test_invalid_or_truncated_model_response_rejected(response):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response))
    ) as c:
        model = OllamaModel(client=c)
        with pytest.raises(ValueError):
            model.generate([], {})
