"""Bounded structured-generation interface; no automatic downloads or retries."""

from time import perf_counter
from typing import Literal, Protocol

import httpx
from pydantic import Field, StrictBool

from causalbridge.schemas import Record


class ModelConfig(Record):
    model: str = "qwen2.5:3b"
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = Field(default=120, gt=0)
    temperature: float = Field(default=0, ge=0, le=2)
    seed: int = 261
    max_tokens: int = Field(default=1024, gt=0)
    context_tokens: int = Field(default=8192, ge=1024)
    think: StrictBool | None = None


class Generation(Record):
    text: str
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_seconds: float = Field(default=0, ge=0)
    status: Literal["complete", "truncated", "incomplete"] = "complete"
    failure_reason: str | None = None
    raw_response: str | None = None


class GenerationFailure(ValueError):
    """A response exists, but its generation must never enter the prediction parser."""

    def __init__(self, generation: Generation):
        self.generation = generation
        super().__init__(generation.failure_reason or "incomplete_generation")


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
        if config.think is not None:
            payload["think"] = config.think
        url = config.base_url.rstrip("/") + "/api/chat"
        if self.client is None:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.post(url, json=payload)
        else:
            response = self.client.post(url, json=payload, timeout=config.timeout_seconds)
        response.raise_for_status()
        body = response.json()
        content = body.get("message", {}).get("content")
        status, reason = "complete", None
        if body.get("done_reason") == "length":
            status, reason = "truncated", "output_token_limit"
        elif body.get("done") is not True:
            status, reason = "incomplete", "response_not_done"
        elif not isinstance(content, str) or not content.strip():
            status, reason = "incomplete", "missing_text_content"
        generation = Generation(
            text=content if isinstance(content, str) else "",
            model=body.get("model", config.model),
            input_tokens=body.get("prompt_eval_count"),
            output_tokens=body.get("eval_count"),
            latency_seconds=perf_counter() - started,
            status=status,
            failure_reason=reason,
            raw_response=response.text,
        )
        if status != "complete":
            raise GenerationFailure(generation)
        return generation
