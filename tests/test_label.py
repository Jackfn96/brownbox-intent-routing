import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from brownbox import label
from brownbox.models import Conversation, GoldLabel, Turn

CHOICES = ["order_status", "cancel_order", "initiate_return"]
KEYS = {"f": "fraud_or_takeover", "w": "wants_human", "c": "complaint"}


def gold(id: int, **overrides: object) -> GoldLabel:
    fields: dict[str, object] = {
        "id": id,
        "primary": "cancel_order",
        "clear_at": 1,
        "mode": "blind",
        "ontology_version": "1",
    }
    return GoldLabel.model_validate(fields | overrides)


@pytest.mark.parametrize(
    ("text", "optional", "expected"),
    [
        ("2", False, "cancel_order"),
        ("0", False, "other"),
        (" 3 ", False, "initiate_return"),
        ("", True, None),
    ],
)
def test_parse_intent(text: str, optional: bool, expected: str | None) -> None:
    assert label.parse_intent(text, CHOICES, optional) == expected


@pytest.mark.parametrize("text", ["", "4", "x", "-1"])
def test_parse_intent_rejects_bad_input(text: str) -> None:
    with pytest.raises(ValueError):
        label.parse_intent(text, CHOICES, optional=False)


def test_parse_message_uses_default_and_bounds() -> None:
    assert label.parse_message("", 3, default=1) == 1
    assert label.parse_message("3", 3, default=1) == 3
    with pytest.raises(ValueError):
        label.parse_message("4", 3, default=1)


def test_parse_guards_records_the_message_each_fires_at() -> None:
    assert label.parse_guards("", KEYS, 5) == {}
    assert label.parse_guards("w5, f", KEYS, 5) == {"fraud_or_takeover": 1, "wants_human": 5}
    with pytest.raises(ValueError, match="unknown guard"):
        label.parse_guards("z", KEYS, 5)
    with pytest.raises(ValueError, match="1 to 5"):
        label.parse_guards("f9", KEYS, 5)


def test_labelling_order_is_fixed_regardless_of_input_order() -> None:
    convs = [
        Conversation(
            id=i, split="practice", turns=(Turn(role="customer", speaker="Customer", text="hi"),)
        )
        for i in range(20)
    ]
    assert label.labelling_order(convs) == label.labelling_order(list(reversed(convs)))


def test_saved_labels_reload(tmp_path: Path) -> None:
    path = tmp_path / "gold" / "practice.jsonl"
    label.save_label(path, gold(1))
    label.save_label(path, gold(2, switch_at=3, switch_to="order_status"))
    assert set(label.load_labels(path)) == {1, 2}


def test_switch_needs_both_fields() -> None:
    with pytest.raises(ValidationError, match="go together"):
        gold(1, switch_at=3)


def test_parse_intent_blank_accepts_the_suggestion() -> None:
    assert label.parse_intent("", CHOICES, optional=False, default="cancel_order") == "cancel_order"
    assert label.parse_intent("3", CHOICES, optional=False, default="cancel_order") == (
        "initiate_return"
    )


def test_suggestions_only_where_every_model_agrees(tmp_path: Path) -> None:
    path = tmp_path / "prelabels.jsonl"
    rows = [
        {"id": 1, "model": "a", "primary": "cancel_order"},
        {"id": 1, "model": "b", "primary": "cancel_order"},
        {"id": 2, "model": "a", "primary": "cancel_order"},
        {"id": 2, "model": "b", "primary": "initiate_return"},
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert label.load_suggestions(path) == {1: "cancel_order"}
