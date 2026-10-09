import pytest
from conftest import MakeSteps
from pydantic import BaseModel

from brownbox import llm
from brownbox.classify import (
    GuardCheck,
    RouterPrompts,
    decide,
    route_conversation,
    router_schema,
)
from brownbox.models import Conversation, Turn
from brownbox.ontology import load_ontology

ONTOLOGY = load_ontology()
USAGE = llm.Usage(
    input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0, latency_s=0.0
)


def test_never_guard_wins_over_any_intent(make_steps: MakeSteps) -> None:
    d = decide(ONTOLOGY, make_steps(("initiate_return", ("fraud_or_takeover",))))
    assert d.outcome == "specialist"


def test_guards_are_sticky(make_steps: MakeSteps) -> None:
    steps = make_steps(("initiate_return", ("wants_human",)), ("initiate_return", ()))
    assert decide(ONTOLOGY, steps).outcome == "human"


def test_unclear_asks_and_other_hands_off(make_steps: MakeSteps) -> None:
    assert decide(ONTOLOGY, make_steps(("unclear", ()))).outcome == "clarify"
    assert decide(ONTOLOGY, make_steps(("other", ()))).outcome == "human"


def test_handoff_intent_goes_to_a_person(make_steps: MakeSteps) -> None:
    assert decide(ONTOLOGY, make_steps(("close_account", ()))).outcome == "human"


def test_ai_intent_goes_to_its_agent_with_signoff_actions(make_steps: MakeSteps) -> None:
    d = decide(ONTOLOGY, make_steps(("initiate_return", ())))
    assert (d.outcome, d.agent) == ("agent", "returns_agent")
    assert any("Waive" in a for a in d.signoff_actions)


def test_router_switches_only_on_a_changed_request_and_checks_each_guard_until_it_fires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = RouterPrompts(
        system="router",
        schema=router_schema(ONTOLOGY),
        guards={"wants_human": "w", "complaint": "c"},
    )
    intents = iter(
        [
            ("unclear", False),
            ("initiate_return", False),  # First real intent: taken although "no change".
            ("refund_status", False),  # A follow-up: the model's topic guess is ignored.
            ("cancel_order", True),  # A real change.
        ]
    )
    checked: list[tuple[str, str]] = []  # (guard prompt, customer's latest message)

    def fake(req: llm.Request, out: type[BaseModel]) -> llm.Reply[BaseModel]:
        if req.system == "router":
            intent, changes = next(intents)
            output: BaseModel = prompts.schema.model_validate(
                {"intent": intent, "changes_request": changes}
            )
        else:
            latest = req.user.splitlines()[-1]
            checked.append((req.system, latest))
            output = GuardCheck(quote="", fires=req.system == "w" and "m1" in latest)
        return llm.Reply(output, USAGE, from_cache=True)

    monkeypatch.setattr(llm, "structured", fake)
    turns = tuple(Turn(role="customer", speaker="Customer", text=f"m{k}") for k in range(4))
    steps = route_conversation(Conversation(id=1, split="synthetic", turns=turns), prompts).steps

    assert [s.intent for s in steps] == [
        "unclear",
        "initiate_return",
        "initiate_return",
        "cancel_order",
    ]
    assert [s.guards for s in steps] == [(), ("wants_human",), (), ()]
    # wants_human fired at the second message, so it is not checked again; complaint always is.
    assert [g for g, _ in checked] == ["w", "c", "w", "c", "c", "c"]


def test_router_schema_offers_unclear_and_other() -> None:
    choices = router_schema(ONTOLOGY).model_json_schema()["properties"]["intent"]["enum"]
    assert {"unclear", "other"} <= set(choices)
