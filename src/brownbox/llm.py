"""Structured Claude calls behind one function, with an on-disk cache.

Every call returns a validated Pydantic object or raises LLMError. Nothing ever falls back
to a default answer: a failed call is reported as a failure.
"""

import dataclasses
import hashlib
import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import cache
from typing import Any, Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field, JsonValue, ValidationError

from brownbox.paths import CACHE

CACHE_DIR = CACHE / "llm"
MAX_ATTEMPTS = 3
# Fail a stuck request fast and retry it. The SDK default (10 min, 2 retries) let one
# hung connection block a worker for half an hour.
TIMEOUT_S = 120.0
SDK_RETRIES = 3
WORKERS = 8  # Parallel calls in run_all.

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


class Price(BaseModel):
    """US dollars per million tokens."""

    input: float
    output: float
    cache_read: float


# Opus 5.5 and Sonnet 5.5 from Anthropic's model docs; Haiku 4.5 from the pricing page.
PRICES = {
    "claude-haiku-4-5": Price(input=1.0, output=5.0, cache_read=0.10),
    "claude-sonnet-5-5": Price(input=2.0, output=10.0, cache_read=0.20),
    "claude-opus-5-5": Price(input=4.0, output=20.0, cache_read=0.20),
}
CACHE_WRITE_MULTIPLIER = 1.25  # 5-minute cache writes cost 1.25x the input price.


def cost(usage: Usage, model: str) -> float:
    """What a call cost in US dollars."""
    p = PRICES[model]
    dollars_per_mtok = (
        usage.input_tokens * p.input
        + usage.cache_write_tokens * p.input * CACHE_WRITE_MULTIPLIER
        + usage.cache_read_tokens * p.cache_read
        + usage.output_tokens * p.output
    )
    return dollars_per_mtok / 1_000_000


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


def one_of(values: list[str], description: str = "") -> Any:
    """A string field whose allowed values are listed in the output schema, so the model can
    only answer with one of them. For choices built at runtime, e.g. ontology ids."""
    choices: list[JsonValue] = [*values]
    return Field(description=description, json_schema_extra={"enum": choices})


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


def run_all[I, O](fn: Callable[[I], O], items: list[I], label: str) -> list[O]:
    """Run fn over items in parallel, keep their order, and print progress as it goes."""
    done: dict[int, O] = {}
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = {pool.submit(fn, item): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            done[futures[future]] = future.result()
            if len(done) % 50 == 0 or len(done) == len(items):
                print(f"  {label}: {len(done)}/{len(items)}", flush=True)
    return [done[i] for i in range(len(items))]
