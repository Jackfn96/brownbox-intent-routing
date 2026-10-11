from conftest import intent_data, ontology_data

from brownbox.models import Conversation, Turn
from brownbox.ontology import Ontology
from brownbox.prompts import format_conversation, render_ontology


def test_format_conversation_labels_customer_and_keeps_staff_names() -> None:
    conv = Conversation(
        id=1,
        split="dev",
        turns=(
            Turn(role="staff", speaker="Agent", text="Hello."),
            Turn(role="customer", speaker="Customer", text="My order is late."),
            Turn(role="staff", speaker="Supervisor", text="Let me check."),
        ),
    )
    assert format_conversation(conv) == (
        "Agent: Hello.\n\nCustomer: My order is late.\n\nSupervisor: Let me check."
    )


def test_format_conversation_numbers_customer_messages() -> None:
    conv = Conversation(
        id=1,
        split="dev",
        turns=(
            Turn(role="customer", speaker="Customer", text="Hi."),
            Turn(role="staff", speaker="Agent", text="Hello."),
            Turn(role="customer", speaker="Customer", text="Cancel it."),
        ),
    )
    assert format_conversation(conv, numbered=True) == (
        "Customer (C1): Hi.\n\nAgent: Hello.\n\nCustomer (C2): Cancel it."
    )


def test_render_ontology_shows_definitions_boundaries_examples_and_guards() -> None:
    cancel = intent_data("cancel_order", boundaries={"order_status": "Cancel ends it."})
    ontology = Ontology.model_validate(ontology_data(cancel, intent_data("order_status")))
    turns = (
        Turn(role="customer", speaker="Customer", text="Cancel my order."),
        Turn(role="staff", speaker="Agent", text="Which one?"),
        Turn(role="customer", speaker="Customer", text="The blender."),
        Turn(role="customer", speaker="Customer", text="Thanks."),
    )
    examples = {i: Conversation(id=i, split="dev", turns=turns) for i in (1, 2)}
    text = render_ontology(ontology, examples)
    assert "### cancel_order: cancel order" in text
    assert "Versus order_status: Cancel ends it." in text
    assert 'Example: "Cancel my order. / The blender."' in text  # The first two customer messages.
    assert "Does not fire on: My parcel was stolen" in text
