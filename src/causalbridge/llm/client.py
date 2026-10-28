"""Bounded structured-generation interface; no automatic downloads or retries."""

from time import perf_counter
from typing import Protocol

import httpx
from pydantic import Field

from causalbridge.schemas import Record


class ModelConfig(Record):
    model: str = "qwen2.5:3b"
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = Field(default=120, gt=0)
    temperature: float = Field(default=0, ge=0, le=2)
    seed: int = 261
    max_tokens: int = Field(default=1024, gt=0)
    context_tokens: int = Field(default=8192, ge=1024)


class Generation(Record):
    text: str
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_seconds: float = Field(default=0, ge=0)


class JSONModel(Protocol):
    def generate(self, messages: list[dict[str, str]], schema: dict) -> Generation: ...


class OllamaModel:
    def __init__(self, config: ModelConfig | None = None, *, client: httpx.Client | None = None):
        self.config = config or ModelConfig()
        self.client = client

    def generate(self, messages: list[dict[str, str]], schema: dict) -> Generation:
        config = self.config
        started = perf_counter()
        payload = dict(
            model=config.model,
            messages=messages,
            format=schema,
            stream=False,
            options=dict(
                temperature=config.temperature,
                seed=config.seed,
                num_predict=config.max_tokens,
                num_ctx=config.context_tokens,
            ),
        )
        url = config.base_url.rstrip("/") + "/api/chat"
        if self.client is None:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.post(url, json=payload)
        else:
            response = self.client.post(url, json=payload, timeout=config.timeout_seconds)
        response.raise_for_status()
        body = response.json()
        if body.get("done") is not True or body.get("done_reason") == "length":
            raise ValueError("Model response incomplete or generation budget exhausted")
        content = body.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Model response has no textual JSON content")
        return Generation(
            text=content,
            model=body.get("model", config.model),
            input_tokens=body.get("prompt_eval_count"),
            output_tokens=body.get("eval_count"),
            latency_seconds=perf_counter() - started,
        )
