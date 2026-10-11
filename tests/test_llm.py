import dataclasses
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from pydantic import BaseModel

from brownbox import llm


class Answer(BaseModel):
    label: str


USAGE = llm.Usage(
    input_tokens=10, output_tokens=2, cache_read_tokens=0, cache_write_tokens=0, latency_s=0.1
)
REQ = llm.Request(model="claude-haiku-4-5", system="Classify.", user="Where is my order?")
Provider = Callable[[llm.Request, type[Answer]], tuple[Answer, llm.Usage]]
UseProvider = Callable[[Provider], list[llm.Request]]


@pytest.fixture(autouse=True)
def cache_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def use_provider(monkeypatch: pytest.MonkeyPatch) -> UseProvider:
    """Replace the real API call with `fake` and record every request it receives."""

    def install(fake: Provider) -> list[llm.Request]:
        calls: list[llm.Request] = []

        def recording(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
            calls.append(req)
            return fake(req, schema)

        monkeypatch.setattr(llm, "_call_provider", recording)
        return calls

    return install


def ok(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
    return schema(label="ok"), USAGE


def test_second_identical_call_comes_from_cache(use_provider: UseProvider) -> None:
    calls = use_provider(ok)
    first = llm.structured(REQ, Answer)
    second = llm.structured(REQ, Answer)
    assert (first.output.label, first.from_cache) == ("ok", False)
    assert (second.output.label, second.from_cache) == ("ok", True)
    assert len(calls) == 1


def test_each_run_has_its_own_cache_slot(use_provider: UseProvider) -> None:
    calls = use_provider(ok)
    llm.structured(REQ, Answer)
    llm.structured(dataclasses.replace(REQ, run=1), Answer)
    assert len(calls) == 2


def test_invalid_output_is_retried(use_provider: UseProvider) -> None:
    attempts: Iterator[Exception | tuple[Answer, llm.Usage]] = iter(
        [llm.InvalidOutput("truncated"), (Answer(label="ok"), USAGE)]
    )

    def flaky(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
        result = next(attempts)
        if isinstance(result, Exception):
            raise result
        return result

    use_provider(flaky)
    assert llm.structured(REQ, Answer).output.label == "ok"


def test_always_invalid_raises_and_caches_nothing(
    use_provider: UseProvider, cache_dir: Path
) -> None:
    def broken(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
        raise llm.InvalidOutput("bad json")

    calls = use_provider(broken)
    with pytest.raises(llm.LLMError):
        llm.structured(REQ, Answer)
    assert len(calls) == llm.MAX_ATTEMPTS
    assert not list(cache_dir.iterdir())


def test_refusal_is_not_retried(use_provider: UseProvider) -> None:
    def refuses(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
        raise llm.LLMError("refused")

    calls = use_provider(refuses)
    with pytest.raises(llm.LLMError):
        llm.structured(REQ, Answer)
    assert len(calls) == 1


def test_cache_key_changes_with_prompt_and_schema() -> None:
    class Other(BaseModel):
        name: str

    base = llm.cache_key(REQ, Answer)
    assert llm.cache_key(dataclasses.replace(REQ, system="Other."), Answer) != base
    assert llm.cache_key(REQ, Other) != base


def test_run_all_keeps_input_order() -> None:
    assert llm.run_all(lambda x: x * 2, list(range(120)), "test") == [x * 2 for x in range(120)]


def test_run_all_stops_queued_work_after_a_failure() -> None:
    started: list[int] = []

    def work(x: int) -> int:
        started.append(x)
        if x == 0:
            raise llm.LLMError("boom")
        time.sleep(0.01)
        return x

    with pytest.raises(llm.LLMError, match="boom"):
        llm.run_all(work, list(range(200)), "test")
    assert len(started) < 200


def test_cache_entries_are_written_whole(use_provider: UseProvider, cache_dir: Path) -> None:
    use_provider(ok)
    llm.structured(REQ, Answer)
    assert [p.suffix for p in cache_dir.iterdir()] == [".json"]


def test_cost_prices_each_kind_of_token() -> None:
    usage = llm.Usage(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        cache_write_tokens=1_000_000,
        latency_s=1.0,
    )
    # Haiku 4.5: $1 input + $5 output + $0.10 cache read + $1.25 cache write.
    assert llm.cost(usage, "claude-haiku-4-5") == pytest.approx(7.35)
