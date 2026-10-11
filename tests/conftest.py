from collections.abc import Callable

import pytest

from brownbox.cases import Case
from brownbox.classify import Step
from brownbox.models import GoldLabel

# One (intent, guards) pair per customer message, from C1.
StepSpec = tuple[str, tuple[str, ...]]
MakeSteps = Callable[..., list[Step]]
MakeGold = Callable[..., GoldLabel]
MakeCase = Callable[..., Case]


@pytest.fixture
def make_steps() -> MakeSteps:
    """Build the router's steps through a conversation, one spec per customer message."""

    def build(*specs: StepSpec) -> list[Step]:
        return [Step(message=k, intent=i, guards=g) for k, (i, g) in enumerate(specs, start=1)]

    return build


@pytest.fixture
def make_gold() -> MakeGold:
    """A gold label: cancel_order, clear from C1, blind, unless overridden."""

    def build(**overrides: object) -> GoldLabel:
        fields: dict[str, object] = {
            "id": 1,
            "primary": "cancel_order",
            "clear_at": 1,
            "mode": "blind",
            "ontology_version": "1",
        }
        return GoldLabel.model_validate(fields | overrides)

    return build


@pytest.fixture
def make_case() -> MakeCase:
    """A hand-written case: a trap with two customer messages, unless overridden."""

    def build(**overrides: object) -> Case:
        fields: dict[str, object] = {
            "id": 9001,
            "kind": "trap",
            "note": "test",
            "turns": [["customer", "a"], ["agent", "b"], ["customer", "c"]],
            "primary": "cancel_order",
        }
        return Case.model_validate(fields | overrides)

    return build


def intent_data(id: str, **overrides: object) -> dict[str, object]:
    """One intent as it appears in ontology.yaml, with valid defaults."""
    return {
        "id": id,
        "name": id.replace("_", " "),
        "domain": "orders",
        "definition": "A customer request.",
        "includes": ["the request"],
        "examples": [1, 2],
        "kind": "act",
        "requires_verification": True,
        "participation": "ai",
        "agent": "orders_agent",
    } | overrides


def ontology_data(*intents: dict[str, object], **overrides: object) -> dict[str, object]:
    """A whole ontology as it appears in ontology.yaml: one domain, one guard."""
    return {
        "version": "1",
        "domains": [{"id": "orders", "name": "Orders"}],
        "intents": list(intents),
        "guards": [
            {
                "id": "fraud",
                "name": "Fraud",
                "definition": "Someone else used the account or card.",
                "fires_on": ["I never placed this order"],
                "not_on": ["My parcel was stolen from my doorstep"],
                "participation": "never",
            }
        ],
    } | overrides
