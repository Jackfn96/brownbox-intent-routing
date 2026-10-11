import pytest
from conftest import MakeGold, MakeSteps

from brownbox.score import (
    acceptable,
    confusions,
    guard_counts,
    label_quality,
    per_intent,
    rate,
    score_conversation,
    share,
)

AGENTS = {"cancel_order": "orders", "order_status": "orders", "initiate_return": "returns"}


def test_nothing_is_expected_before_the_intent_is_clear(make_gold: MakeGold) -> None:
    label = make_gold(
        clear_at=2, secondary="order_status", switch_at=3, switch_to="initiate_return"
    )
    assert acceptable(label, 1) is None
    assert acceptable(label, 2) == {"cancel_order", "order_status"}
    assert acceptable(label, 3) == {"initiate_return"}


def test_same_intent_as_second_request_and_switch_is_a_request_added_then(
    make_steps: MakeSteps, make_gold: MakeGold
) -> None:
    label = make_gold(secondary="initiate_return", switch_at=2, switch_to="initiate_return")
    assert acceptable(label, 1) == {"cancel_order"}
    assert acceptable(label, 2) == {"cancel_order", "initiate_return"}
    steps = make_steps(("cancel_order", ()), ("cancel_order", ()))
    s = score_conversation(label, steps, AGENTS)
    assert s.messages_correct == 2 and not s.switch_missed and s.switch_delay is None


def test_a_right_conversation_scores_fully(make_steps: MakeSteps, make_gold: MakeGold) -> None:
    steps = make_steps(("unclear", ()), ("cancel_order", ()), ("cancel_order", ()))
    s = score_conversation(make_gold(clear_at=2), steps, AGENTS)
    assert s.correct_at_clear and s.final_correct
    assert (s.messages_correct, s.messages_scored, s.false_switches) == (2, 2, 0)


def test_wrong_intent_for_the_same_agent_is_counted_separately(
    make_steps: MakeSteps, make_gold: MakeGold
) -> None:
    s = score_conversation(make_gold(), make_steps(("order_status", ())), AGENTS)
    assert not s.correct_at_clear and s.agent_correct_at_clear


def test_leaving_a_right_intent_is_a_false_switch(
    make_steps: MakeSteps, make_gold: MakeGold
) -> None:
    steps = make_steps(("cancel_order", ()), ("initiate_return", ()), ("cancel_order", ()))
    s = score_conversation(make_gold(), steps, AGENTS)
    assert s.false_switches == 1 and s.final_correct


def test_switch_delay_counts_messages_until_the_router_follows(
    make_steps: MakeSteps, make_gold: MakeGold
) -> None:
    label = make_gold(switch_at=2, switch_to="initiate_return")
    late = make_steps(("cancel_order", ()), ("cancel_order", ()), ("initiate_return", ()))
    never = make_steps(("cancel_order", ()), ("cancel_order", ()))
    assert score_conversation(label, late, AGENTS).switch_delay == 1
    assert score_conversation(label, never, AGENTS).switch_missed
    # Following a real switch is not a false switch.
    assert score_conversation(label, late, AGENTS).false_switches == 0


def test_guards_record_where_they_first_fired(make_steps: MakeSteps, make_gold: MakeGold) -> None:
    label = make_gold(guards={"wants_human": 2})
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


def test_label_quality_compares_only_where_models_fully_agree(make_gold: MakeGold) -> None:
    mine = {
        1: make_gold(id=1, mode="blind"),
        2: make_gold(id=2, mode="assisted"),
        3: make_gold(id=3, mode="assisted", secondary="order_status"),
        4: make_gold(id=4, mode="assisted"),  # Models disagreed: no silver label.
    }
    silver = {i: make_gold(id=i, mode="silver") for i in (1, 2, 3)}
    q = label_quality(mine, silver)
    assert (q.blind_primary.hits, q.blind_primary.total) == (1, 1)
    assert (q.audit_primary.hits, q.audit_primary.total) == (2, 2)
    assert (q.audit_full.hits, q.audit_full.total) == (1, 2)


def test_guard_precision_and_recall(make_steps: MakeSteps, make_gold: MakeGold) -> None:
    hit = score_conversation(
        make_gold(id=1, guards={"wants_human": 1}),
        make_steps(("cancel_order", ("wants_human",))),
        AGENTS,
    )
    missed = score_conversation(
        make_gold(id=2, guards={"wants_human": 1}), make_steps(("cancel_order", ())), AGENTS
    )
    false_alarm = score_conversation(
        make_gold(id=3), make_steps(("cancel_order", ("wants_human",))), AGENTS
    )
    c = guard_counts([hit, missed, false_alarm], ["wants_human"])["wants_human"]
    assert (c.recall.hits, c.recall.total) == (1, 2)
    assert (c.precision.hits, c.precision.total) == (1, 2)
    assert (c.flag_rate.hits, c.flag_rate.total) == (2, 3)


def test_per_intent_and_confusions(make_steps: MakeSteps, make_gold: MakeGold) -> None:
    scores = [
        score_conversation(make_gold(id=1), make_steps(("cancel_order", ())), AGENTS),
        score_conversation(make_gold(id=2), make_steps(("order_status", ())), AGENTS),
        score_conversation(
            make_gold(id=3, primary="initiate_return"), make_steps(("initiate_return", ())), AGENTS
        ),
    ]
    stats = per_intent(scores)
    assert list(stats)[0] == "cancel_order"  # Most-labelled first.
    assert stats["cancel_order"].recall.value == pytest.approx(0.5)
    assert stats["cancel_order"].precision.value == 1
    assert stats["order_status"].support == 0 and stats["order_status"].f1 is None
    assert [(c.expected, c.got, c.count, c.same_agent) for c in confusions(scores)] == [
        ("cancel_order", "order_status", 1, True)
    ]


def test_other_and_unclear_are_not_the_same_agent(
    make_steps: MakeSteps, make_gold: MakeGold
) -> None:
    s = score_conversation(make_gold(primary="other"), make_steps(("unclear", ())), AGENTS)
    assert not s.agent_correct_at_clear
