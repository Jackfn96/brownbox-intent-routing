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
    assert label.parse_guards("w5, f1", KEYS, 5) == {"fraud_or_takeover": 1, "wants_human": 5}
    with pytest.raises(ValueError, match="unknown guard"):
        label.parse_guards("z1", KEYS, 5)
    with pytest.raises(ValueError, match="1 to 5"):
        label.parse_guards("w", KEYS, 5)
    with pytest.raises(ValueError, match="1 to 5"):
        label.parse_guards("f9", KEYS, 5)


def test_describe_shows_every_field() -> None:
    names = {"cancel_order": "Cancel order", "initiate_return": "Initiate return"}
    card = label.describe(
        gold(1, switch_at=3, switch_to="initiate_return", guards={"wants_human": 4}), names
    )
    assert "Cancel order, clear from C1" in card
    assert "Second    none" in card
    assert "at C3 to Initiate return" in card
    assert "wants_human from C4" in card


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


def test_adjudication_keeps_the_original_and_the_latest_correction_wins(tmp_path: Path) -> None:
    path = tmp_path / "adjudicated.jsonl"
    original = gold(1, guards={"complaint": 3})
    label.adjudicate(path, original, {"guards": {}}, "dissatisfaction, nothing asked for")
    label.adjudicate(path, original, {"primary": "order_status"}, "second look")
    assert label.load_adjudicated(path)[1].primary == "order_status"
    assert original.guards == {"complaint": 3}
    with pytest.raises(ValidationError):
        label.adjudicate(path, original, {"switch_at": 2}, "switch_at without switch_to")


def test_switch_needs_both_fields() -> None:
    with pytest.raises(ValidationError, match="go together"):
        gold(1, switch_at=3)


def test_parse_intent_blank_accepts_the_suggestion() -> None:
    assert label.parse_intent("", CHOICES, optional=False, default="cancel_order") == "cancel_order"
    assert label.parse_intent("3", CHOICES, optional=False, default="cancel_order") == (
        "initiate_return"
    )


def test_suggestions_only_where_every_model_agrees(tmp_path: Path) -> None:
    def row(id: int, model: str, primary: str, secondary: str | None = None) -> dict[str, object]:
        return {
            "id": id,
            "model": model,
            "primary": primary,
            "secondary": secondary,
            "clear_at": 1,
            "switch_at": None,
            "switch_to": None,
            "guards": {},
        }

    path = tmp_path / "prelabels.jsonl"
    rows = [
        row(1, "a", "cancel_order"),
        row(1, "b", "cancel_order"),
        row(2, "a", "cancel_order"),
        row(2, "b", "initiate_return"),
        row(3, "a", "cancel_order"),
        row(3, "b", "cancel_order", secondary="order_status"),
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    suggestions = label.load_suggestions(path, ontology_version="1")
    assert suggestions.primary == {1: "cancel_order", 3: "cancel_order"}
    assert list(suggestions.agreed) == [1]
    assert suggestions.agreed[1].mode == "silver"


def test_assisted_batch_keeps_disagreements_and_audits_the_first_agreed() -> None:
    convs = [Conversation(id=i, split="practice", turns=()) for i in range(1, 7)]
    batch = label.assisted_batch(convs, agreed=frozenset({1, 3, 4, 6}), audit_size=2)
    assert [c.id for c in batch] == [1, 2, 3, 5]
