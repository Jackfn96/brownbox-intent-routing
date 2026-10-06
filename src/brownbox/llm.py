"""Structured Claude calls behind one function, with an on-disk cache.

Every call returns a validated Pydantic object or raises LLMError. Nothing ever falls back
to a default answer: a failed call is reported as a failure.
"""

import dataclasses
import hashlib
import json
import time
from dataclasses import dataclass
from functools import cache
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from brownbox.paths import CACHE

CACHE_DIR = CACHE / "llm"
MAX_ATTEMPTS = 3
# Fail a stuck request fast and retry it. The SDK default (10 min, 2 retries) let one
# hung connection block a worker for half an hour.
TIMEOUT_S = 120.0
SDK_RETRIES = 3

# Models that accept Anthropic's server-side refusal fallback in its "default" form.
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"

Effort = Literal["low", "medium", "high"]


class LLMError(RuntimeError):
    """The model gave no usable answer: it refused, or every attempt was invalid."""


class InvalidOutput(Exception):
    """The model answered, but not in the requested shape. Worth another attempt."""


@dataclass(frozen=True)
class Request:
    model: str
    system: str
    user: str
    max_tokens: int = 1024
    effort: Effort | None = None
    run: int = 0  # Separate cache slot per run, for measuring run-to-run agreement.


class Usage(BaseModel):
    input_tokens: int  # Uncached input.
    output_tokens: int
    cache_read_tokens: int  # Read from the prompt cache (cheap).
    cache_write_tokens: int  # Written to the prompt cache (1.25x).
    latency_s: float


@dataclass(frozen=True)
class Reply[T: BaseModel]:
    output: T
    usage: Usage
    from_cache: bool


def structured[T: BaseModel](req: Request, schema: type[T]) -> Reply[T]:
    """Call the model for `req` and return its answer validated against `schema`."""
    path = CACHE_DIR / f"{cache_key(req, schema)}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        output = schema.model_validate(cached["output"])
        return Reply(output, Usage.model_validate(cached["usage"]), from_cache=True)

    errors = []
    for _ in range(MAX_ATTEMPTS):
        try:
            output, usage = _call_provider(req, schema)
        except InvalidOutput as e:
            errors.append(str(e))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"output": output.model_dump(mode="json"), "usage": usage.model_dump()}
        path.write_text(json.dumps(record))
        return Reply(output, usage, from_cache=False)
    raise LLMError(f"{req.model}: no valid output after {MAX_ATTEMPTS} attempts: {errors}")


def cache_key(req: Request, schema: type[BaseModel]) -> str:
    payload = {**dataclasses.asdict(req), "schema": schema.model_json_schema()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@cache
def _client() -> anthropic.Anthropic:
    load_dotenv()  # ANTHROPIC_API_KEY from .env; a variable already set in the shell wins.
    return anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=SDK_RETRIES)


def _call_provider[T: BaseModel](req: Request, schema: type[T]) -> tuple[T, Usage]:
    fallback = req.model in FALLBACK_MODELS
    start = time.perf_counter()
    try:
        msg = _client().beta.messages.parse(
            model=req.model,
            max_tokens=req.max_tokens,
            # Cache the system prompt, which is the same on every call. The user message
            # changes each time, so caching it would pay the write cost for nothing.
            system=[{"type": "text", "text": req.system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": req.user}],
            output_format=schema,
            output_config={"effort": req.effort} if req.effort else anthropic.omit,
            betas=[FALLBACK_BETA] if fallback else anthropic.omit,
            fallbacks="default" if fallback else anthropic.omit,
        )
    except ValidationError as e:
        raise InvalidOutput(str(e)) from e
    latency = time.perf_counter() - start

    if msg.stop_reason == "refusal":
        raise LLMError(f"{req.model} refused: {msg.stop_details}")
    if msg.parsed_output is None:
        raise InvalidOutput(f"no parsed output (stop_reason={msg.stop_reason})")
    return msg.parsed_output, Usage(
        input_tokens=msg.usage.input_tokens,
        output_tokens=msg.usage.output_tokens,
        cache_read_tokens=msg.usage.cache_read_input_tokens or 0,
        cache_write_tokens=msg.usage.cache_creation_input_tokens or 0,
        latency_s=latency,
    )
