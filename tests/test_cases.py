import pytest
from conftest import MakeCase
from pydantic import ValidationError

from brownbox.cases import problems
from brownbox.ontology import load_ontology

ONTOLOGY = load_ontology()


FRAUD: dict[str, object] = {
    "kind": "guard",
    "turns": [
        ["customer", "I never placed this order"],
        ["agent", "Sorry."],
        ["customer", "Cancel it."],
    ],
    "guards": {"fraud_or_takeover": 1},
}


def test_valid_case_converts_to_conversation_and_label(make_case: MakeCase) -> None:
    c = make_case(**FRAUD)
    assert problems([c], ONTOLOGY) == []
    assert [t.role for t in c.conversation().turns] == ["customer", "staff", "customer"]
    assert c.label("1").guards == {"fraud_or_takeover": 1}


def test_kind_must_match_fields(make_case: MakeCase) -> None:
    with pytest.raises(ValidationError, match="kind 'trap'"):
        make_case(guards={"fraud_or_takeover": 1})  # A trap must not expect a guard.


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"primary": "refund_everything"}, "unknown primary intent"),
        ({"guards": {"psychic": 1}}, "unknown guard"),
        ({"guards": {"fraud_or_takeover": 3}}, "message 3 but only 2"),
    ],
)
def test_problems_are_reported(
    overrides: dict[str, object], message: str, make_case: MakeCase
) -> None:
    assert any(message in p for p in problems([make_case(**FRAUD | overrides)], ONTOLOGY))
