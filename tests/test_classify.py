from brownbox.classify import Step, decide, router_schema
from brownbox.ontology import load_ontology

ONTOLOGY = load_ontology()


def step(intent: str, guards: tuple[str, ...] = (), message: int = 1) -> Step:
    return Step(message=message, intent=intent, guards=guards)


def test_never_guard_wins_over_any_intent() -> None:
    d = decide(ONTOLOGY, [step("initiate_return", ("fraud_or_takeover",))])
    assert d.outcome == "specialist"


def test_guards_are_sticky() -> None:
    steps = [step("initiate_return", ("wants_human",), 1), step("initiate_return", (), 2)]
    assert decide(ONTOLOGY, steps).outcome == "human"


def test_unclear_asks_and_other_hands_off() -> None:
    assert decide(ONTOLOGY, [step("unclear")]).outcome == "clarify"
    assert decide(ONTOLOGY, [step("other")]).outcome == "human"


def test_handoff_intent_goes_to_a_person() -> None:
    assert decide(ONTOLOGY, [step("close_account")]).outcome == "human"


def test_ai_intent_goes_to_its_agent_with_signoff_actions() -> None:
    d = decide(ONTOLOGY, [step("initiate_return")])
    assert (d.outcome, d.agent) == ("agent", "returns_agent")
    assert any("Waive" in a for a in d.signoff_actions)


def test_router_schema_offers_unclear_and_other() -> None:
    choices = router_schema(ONTOLOGY).model_json_schema()["properties"]["intent"]["enum"]
    assert {"unclear", "other"} <= set(choices)
