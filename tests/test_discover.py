import numpy as np

from brownbox import discover
from brownbox.models import Conversation, Turn
from brownbox.prompts import format_conversation


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


def test_number_by_size_makes_the_largest_cluster_1() -> None:
    labels = np.array([7, 3, 3, 3, 0, 0, 7, 0, 5], dtype=np.int64)
    # Sizes: 3 -> 3, 0 -> 3, 7 -> 2, 5 -> 1. Ties keep the clusterer's order (0 before 3).
    assert discover.number_by_size(labels).tolist() == [3, 2, 2, 2, 1, 1, 3, 1, 4]


def test_cluster_separates_obvious_groups_and_is_repeatable() -> None:
    rng = np.random.default_rng(0)
    a = rng.normal([1, 0, 0], 0.01, size=(10, 3))
    b = rng.normal([0, 1, 0], 0.01, size=(10, 3))
    vectors = np.vstack([a, b]).astype(np.float32)
    labels = discover.cluster(vectors, 2)
    assert len(set(labels[:10])) == 1 and len(set(labels[10:])) == 1
    assert labels[0] != labels[10]
    assert (discover.cluster(vectors, 2) == labels).all()


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
