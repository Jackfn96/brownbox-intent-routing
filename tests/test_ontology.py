import pytest
from conftest import intent_data as intent
from conftest import ontology_data as ontology
from pydantic import ValidationError

from brownbox.ontology import Ontology, non_dev_examples, render_markdown


def test_valid_ontology_loads() -> None:
    o = Ontology.model_validate(
        ontology(
            intent("cancel_order", boundaries={"change_address": "Cancel stops the order."}),
            intent("change_address"),
        )
    )
    assert [i.id for i in o.intents] == ["cancel_order", "change_address"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (ontology(intent("cancel_order"), intent("cancel_order")), "duplicate id: cancel_order"),
        (ontology(intent("unclear")), "reserved id: unclear"),
        (ontology(intent("cancel_order", domain="billing")), "unknown domain billing"),
        (ontology(intent("cancel_order", boundaries={"refund": "x"})), "unknown intent refund"),
        (
            ontology(intent("cancel_order", hands_over_to=["warranty_agent"])),
            "hand-over to unknown agent warranty_agent",
        ),
        (
            ontology(intent("cancel_order", hands_over_to=["orders_agent"])),
            "hand-over to unknown agent orders_agent",  # Its own agent: not a hand-over.
        ),
        (ontology(intent("cancel_order", boundaries={"cancel_order": "x"})), "unknown intent"),
        (ontology(intent("cancel_order", participation="sometimes")), "participation"),
        # Sign-off is per action now (signoff_actions), not an intent-level participation.
        (ontology(intent("cancel_order", participation="ai_with_signoff")), "participation"),
        (ontology(intent("cancel_order", examples=[1])), "examples"),
        (ontology(intent("Cancel Order")), "pattern"),
        (ontology(intent("cancel_order", definiton="typo")), "definiton"),
    ],
)
def test_invalid_ontology_is_rejected(data: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Ontology.model_validate(data)


def test_non_dev_examples_are_reported() -> None:
    o = Ontology.model_validate(ontology(intent("cancel_order", examples=[1, 999])))
    assert non_dev_examples(o, dev_ids={1, 2}) == ["cancel_order: #999"]


def test_render_markdown_lists_every_intent_and_guard() -> None:
    o = Ontology.model_validate(
        ontology(intent("cancel_order", signoff_actions=["Refund to another card"]))
    )
    text = render_markdown(o)
    assert "### cancel order (`cancel_order`)" in text
    assert "**Needs sign-off:** Refund to another card" in text
    assert "### Fraud (`fraud`): Never" in text
