import pytest
from conftest import MakeSteps

from brownbox import llm
from brownbox.classify import decide
from brownbox.models import Conversation, Turn
from brownbox.ontology import load_ontology
from brownbox.route import (
    CLARIFYING_QUESTION,
    Clarification,
    clarify_system,
    clarifying_question,
    describe,
)

ONTOLOGY = load_ontology()


def show(steps: MakeSteps, *specs: tuple[str, tuple[str, ...]]) -> str:
    built = steps(*specs)
    return describe(built, decide(ONTOLOGY, built), ONTOLOGY)


def test_agent_route_names_the_intent_agent_and_signoff_actions(make_steps: MakeSteps) -> None:
    out = show(make_steps, ("unclear", ()), ("initiate_return", ()))
    assert out.startswith("C2  intent: Return, replace or report a faulty item")
    assert "guards so far: none" in out
    assert "(agent returns_agent)" in out
    assert out.count("needs sign-off:") == 3


def test_a_fired_guard_stays_on_later_messages(make_steps: MakeSteps) -> None:
    out = show(make_steps, ("initiate_return", ("fraud_or_takeover",)), ("initiate_return", ()))
    assert "guards so far: fraud_or_takeover" in out
    assert "Hand to the specialist team (never automated)" in out
    assert "needs sign-off" not in out


def test_unclear_and_other_show_their_ids(make_steps: MakeSteps) -> None:
    assert "intent: unclear" in show(make_steps, ("unclear", ()))
    assert "Ask a clarifying question" in show(make_steps, ("unclear", ()))
    assert "Hand to a person" in show(make_steps, ("other", ()))


CONV = Conversation(
    id=0,
    split="synthetic",
    turns=(Turn(role="customer", speaker="Customer", text="Hi, I need help."),),
)
USAGE = llm.Usage(
    input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0, latency_s=0.0
)


def test_clarifying_question_names_the_intents_and_asks_what_the_model_wrote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system = clarify_system(ONTOLOGY)
    assert "- Return policy and process" in system

    def fake(req: llm.Request, schema: type[Clarification]) -> llm.Reply[Clarification]:
        return llm.Reply(schema(question="Is that a return?"), USAGE, from_cache=False)

    monkeypatch.setattr(llm, "structured", fake)
    assert clarifying_question(CONV, system, "claude-haiku-4-5") == "Is that a return?"


def test_clarifying_question_falls_back_if_the_call_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(req: llm.Request, schema: type[Clarification]) -> llm.Reply[Clarification]:
        raise llm.LLMError("down")

    monkeypatch.setattr(llm, "structured", failing)
    assert clarifying_question(CONV, "system", "claude-haiku-4-5") == CLARIFYING_QUESTION
