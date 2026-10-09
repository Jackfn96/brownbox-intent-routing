from typing import Any

import pytest
from conftest import MakeSteps

from brownbox.models import GoldLabel
from brownbox.score import (
    acceptable,
    guard_counts,
    label_quality,
    rate,
    score_conversation,
    share,
)

AGENTS = {"cancel_order": "orders", "order_status": "orders", "initiate_return": "returns"}


def gold(**overrides: Any) -> GoldLabel:
    fields: dict[str, Any] = {
        "id": 1,
        "primary": "cancel_order",
        "clear_at": 1,
        "mode": "blind",
        "ontology_version": "1",
    }
    return GoldLabel.model_validate(fields | overrides)


def test_nothing_is_expected_before_the_intent_is_clear() -> None:
    label = gold(clear_at=2, secondary="order_status", switch_at=3, switch_to="initiate_return")
    assert acceptable(label, 1) is None
    assert acceptable(label, 2) == {"cancel_order", "order_status"}
    assert acceptable(label, 3) == {"initiate_return"}


def test_same_intent_as_second_request_and_switch_is_a_request_added_then(
    make_steps: MakeSteps,
) -> None:
    label = gold(secondary="initiate_return", switch_at=2, switch_to="initiate_return")
    assert acceptable(label, 1) == {"cancel_order"}
    assert acceptable(label, 2) == {"cancel_order", "initiate_return"}
    steps = make_steps(("cancel_order", ()), ("cancel_order", ()))
    s = score_conversation(label, steps, AGENTS)
    assert s.messages_correct == 2 and not s.switch_missed and s.switch_delay is None


def test_a_right_conversation_scores_fully(make_steps: MakeSteps) -> None:
    steps = make_steps(("unclear", ()), ("cancel_order", ()), ("cancel_order", ()))
    s = score_conversation(gold(clear_at=2), steps, AGENTS)
    assert s.correct_at_clear and s.final_correct
    assert (s.messages_correct, s.messages_scored, s.false_switches) == (2, 2, 0)


def test_wrong_intent_for_the_same_agent_is_counted_separately(make_steps: MakeSteps) -> None:
    s = score_conversation(gold(), make_steps(("order_status", ())), AGENTS)
    assert not s.correct_at_clear and s.agent_correct_at_clear


def test_leaving_a_right_intent_is_a_false_switch(make_steps: MakeSteps) -> None:
    steps = make_steps(("cancel_order", ()), ("initiate_return", ()), ("cancel_order", ()))
    s = score_conversation(gold(), steps, AGENTS)
    assert s.false_switches == 1 and s.final_correct


def test_switch_delay_counts_messages_until_the_router_follows(make_steps: MakeSteps) -> None:
    label = gold(switch_at=2, switch_to="initiate_return")
    late = make_steps(("cancel_order", ()), ("cancel_order", ()), ("initiate_return", ()))
    never = make_steps(("cancel_order", ()), ("cancel_order", ()))
    assert score_conversation(label, late, AGENTS).switch_delay == 1
    assert score_conversation(label, never, AGENTS).switch_missed
    # Following a real switch is not a false switch.
    assert score_conversation(label, late, AGENTS).false_switches == 0


def test_guards_record_where_they_first_fired(make_steps: MakeSteps) -> None:
    label = gold(guards={"wants_human": 2})
    steps = make_steps(
        ("cancel_order", ()), ("cancel_order", ()), ("cancel_order", ("wants_human",))
    )
    s = score_conversation(label, steps, AGENTS)
    counts = guard_counts([s], ["wants_human", "complaint"])
    assert counts["wants_human"].caught == 1 and counts["wants_human"].delays == [1]
    assert counts["complaint"].fired == 0


def test_rate_interval_contains_the_value() -> None:
    r = rate([1, 1, 1, 0], [1, 1, 1, 1])
    assert r.value == pytest.approx(0.75)
    assert 0 <= r.low <= r.value <= r.high <= 1


def test_share_gives_a_real_interval_at_100_percent() -> None:
    r = share([True] * 25)
    assert r.value == 1 and r.high == 1
    assert r.low == pytest.approx(0.867, abs=0.001)  # Wilson, 95%.
    assert (share([]).low, share([]).high) == (0.0, 1.0)


def test_message_rate_weights_by_messages() -> None:
    assert rate([3, 0], [3, 1]).value == pytest.approx(0.75)


def test_label_quality_compares_only_where_models_fully_agree() -> None:
    mine = {
        1: gold(id=1, mode="blind"),
        2: gold(id=2, mode="assisted"),
        3: gold(id=3, mode="assisted", secondary="order_status"),
        4: gold(id=4, mode="assisted"),  # Models disagreed: no silver label.
    }
    silver = {i: gold(id=i, mode="silver") for i in (1, 2, 3)}
    q = label_quality(mine, silver)
    assert (q.blind_primary.hits, q.blind_primary.total) == (1, 1)
    assert (q.audit_primary.hits, q.audit_primary.total) == (2, 2)
    assert (q.audit_full.hits, q.audit_full.total) == (1, 2)
