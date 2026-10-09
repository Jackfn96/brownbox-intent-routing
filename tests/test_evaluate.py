from pathlib import Path

import pytest
from conftest import MakeCase, MakeGold, MakeSteps

from brownbox import evaluate, llm
from brownbox.classify import Routing
from brownbox.evaluate import build_report, score_case
from brownbox.models import Conversation, Turn
from brownbox.ontology import load_ontology


def test_guard_must_fire_at_the_expected_message(
    make_steps: MakeSteps, make_case: MakeCase
) -> None:
    c = make_case(kind="guard", guards={"fraud_or_takeover": 2})
    on_time = make_steps(("cancel_order", ()), ("cancel_order", ("fraud_or_takeover",)))
    late = make_steps(("cancel_order", ()), ("cancel_order", ()))
    assert score_case(c, on_time).passed
    assert "never fired" in score_case(c, late).detail


def test_trap_fails_if_any_guard_fires(make_steps: MakeSteps, make_case: MakeCase) -> None:
    steps = make_steps(("cancel_order", ("fraud_or_takeover",)), ("cancel_order", ()))
    result = score_case(make_case(), steps)
    assert not result.passed and "shouldn't" in result.detail


def test_switch_must_be_followed(make_steps: MakeSteps, make_case: MakeCase) -> None:
    c = make_case(kind="switch", switch_at=2, switch_to="initiate_return")
    assert score_case(c, make_steps(("cancel_order", ()), ("initiate_return", ()))).passed
    assert not score_case(c, make_steps(("cancel_order", ()), ("cancel_order", ()))).passed


def test_steady_fails_on_a_flip(make_steps: MakeSteps, make_case: MakeCase) -> None:
    c = make_case(kind="steady")
    assert not score_case(c, make_steps(("cancel_order", ()), ("order_status", ()))).passed


def test_report_counts_false_alarms_only_where_no_guard_was_expected(
    make_steps: MakeSteps, make_gold: MakeGold
) -> None:
    turns = (Turn(role="customer", speaker="Customer", text="Hi."),)
    convs = [Conversation(id=i, split="practice", turns=turns) for i in (1, 2, 3)]
    labels = {
        1: make_gold(id=1),
        2: make_gold(id=2, guards={"wants_human": 1}),
        3: make_gold(id=3),
    }
    usage = llm.Usage(
        input_tokens=1_000_000,
        output_tokens=0,
        cache_read_tokens=0,
        cache_write_tokens=0,
        latency_s=1,
    )
    routings = [
        Routing(make_steps(("cancel_order", ("complaint",))), [usage]),  # A false alarm.
        Routing(make_steps(("cancel_order", ("wants_human",))), [usage]),  # Expected: not one.
        Routing(make_steps(("order_status", ())), [usage]),  # Wrong intent, same agent.
    ]
    r = build_report(
        "practice", convs, labels, "mine", None, routings, load_ontology(), "claude-haiku-4-5", None
    )
    assert (r.false_alarms.hits, r.false_alarms.total) == (1, 2)
    assert (r.intent_at_clear.hits, r.agent_at_clear.hits) == (2, 3)
    assert r.guards["wants_human"].recall.value == 1
    assert r.cost_usd == pytest.approx(3.0)  # Haiku input is $1 per million tokens.


def test_pooled_guards_need_every_saved_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(evaluate, "EVAL_DIR", tmp_path)
    with pytest.raises(SystemExit, match="no saved cases results"):
        evaluate.run_guards("claude-haiku-4-5", None)
