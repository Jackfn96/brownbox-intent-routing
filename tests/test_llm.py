from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import BaseModel

from brownbox import llm


class Answer(BaseModel):
    label: str


USAGE = llm.Usage(input_tokens=10, output_tokens=2, cached_input_tokens=0, latency_s=0.1)
REQ = llm.Request(model="claude-haiku-4-5", system="Classify.", user="Where is my order?")


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[llm.Request]:
    """Point the cache at a temp dir and record every provider call. Default reply: 'ok'."""
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    made: list[llm.Request] = []

    def fake(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
        made.append(req)
        return schema(label="ok"), USAGE

    monkeypatch.setattr(llm, "_call_provider", fake)
    return made


def test_second_identical_call_comes_from_cache(calls: list[llm.Request]) -> None:
    first = llm.structured(REQ, Answer)
    second = llm.structured(REQ, Answer)
    assert (first.output.label, first.from_cache) == ("ok", False)
    assert (second.output.label, second.from_cache) == ("ok", True)
    assert len(calls) == 1


def test_each_run_has_its_own_cache_slot(calls: list[llm.Request]) -> None:
    llm.structured(REQ, Answer)
    llm.structured(llm.Request(**{**REQ.__dict__, "run": 1}), Answer)
    assert len(calls) == 2


def test_invalid_output_is_retried(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    attempts: Iterator[Exception | tuple[Answer, llm.Usage]] = iter(
        [llm.InvalidOutput("truncated"), (Answer(label="ok"), USAGE)]
    )

    def flaky(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
        result = next(attempts)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(llm, "_call_provider", flaky)
    assert llm.structured(REQ, Answer).output.label == "ok"


def test_always_invalid_raises_instead_of_defaulting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    count = 0

    def broken(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
        nonlocal count
        count += 1
        raise llm.InvalidOutput("bad json")

    monkeypatch.setattr(llm, "_call_provider", broken)
    with pytest.raises(llm.LLMError):
        llm.structured(REQ, Answer)
    assert count == llm.MAX_ATTEMPTS
    assert not list(tmp_path.iterdir())  # Failures are never cached.


def test_refusal_is_not_retried(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    count = 0

    def refuses(req: llm.Request, schema: type[Answer]) -> tuple[Answer, llm.Usage]:
        nonlocal count
        count += 1
        raise llm.LLMError("refused")

    monkeypatch.setattr(llm, "_call_provider", refuses)
    with pytest.raises(llm.LLMError):
        llm.structured(REQ, Answer)
    assert count == 1


def test_cache_key_changes_with_prompt_and_schema() -> None:
    class Other(BaseModel):
        name: str

    base = llm.cache_key(REQ, Answer)
    assert llm.cache_key(llm.Request(**{**REQ.__dict__, "system": "Other."}), Answer) != base
    assert llm.cache_key(REQ, Other) != base
