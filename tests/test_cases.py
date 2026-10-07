from typing import Any

import pytest
from pydantic import ValidationError

from brownbox.cases import Case, problems
from brownbox.ontology import load_ontology

ONTOLOGY = load_ontology()


def case(**overrides: Any) -> Case:
    fields: dict[str, Any] = {
        "id": 9001,
        "kind": "guard",
        "note": "test",
        "turns": [
            ["customer", "I never placed this order"],
            ["agent", "Sorry."],
            ["customer", "Cancel it."],
        ],
        "primary": "cancel_order",
        "guards": {"fraud_or_takeover": 1},
    }
    return Case.model_validate(fields | overrides)


def test_valid_case_converts_to_conversation_and_label() -> None:
    c = case()
    assert problems([c], ONTOLOGY) == []
    assert [t.role for t in c.conversation().turns] == ["customer", "staff", "customer"]
    assert c.label("1").guards == {"fraud_or_takeover": 1}


def test_kind_must_match_fields() -> None:
    with pytest.raises(ValidationError, match="kind 'trap'"):
        case(kind="trap")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"primary": "refund_everything"}, "unknown primary intent"),
        ({"guards": {"psychic": 1}}, "unknown guard"),
        ({"guards": {"fraud_or_takeover": 3}}, "message 3 but only 2"),
    ],
)
def test_problems_are_reported(overrides: dict[str, Any], message: str) -> None:
    assert any(message in p for p in problems([case(**overrides)], ONTOLOGY))
