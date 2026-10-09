from typing import Any

from conftest import MakeSteps

from brownbox.cases import Case
from brownbox.evaluate import score_case


def case(**overrides: Any) -> Case:
    fields: dict[str, Any] = {
        "id": 9001,
        "kind": "trap",
        "note": "test",
        "turns": [["customer", "a"], ["agent", "b"], ["customer", "c"]],
        "primary": "cancel_order",
    }
    return Case.model_validate(fields | overrides)


def test_guard_must_fire_at_the_expected_message(make_steps: MakeSteps) -> None:
    c = case(kind="guard", guards={"fraud_or_takeover": 2})
    on_time = make_steps(("cancel_order", ()), ("cancel_order", ("fraud_or_takeover",)))
    late = make_steps(("cancel_order", ()), ("cancel_order", ()))
    assert score_case(c, on_time).passed
    assert "never fired" in score_case(c, late).detail


def test_trap_fails_if_any_guard_fires(make_steps: MakeSteps) -> None:
    steps = make_steps(("cancel_order", ("fraud_or_takeover",)), ("cancel_order", ()))
    result = score_case(case(), steps)
    assert not result.passed and "shouldn't" in result.detail


def test_switch_must_be_followed(make_steps: MakeSteps) -> None:
    c = case(kind="switch", switch_at=2, switch_to="initiate_return")
    assert score_case(c, make_steps(("cancel_order", ()), ("initiate_return", ()))).passed
    assert not score_case(c, make_steps(("cancel_order", ()), ("cancel_order", ()))).passed


def test_steady_fails_on_a_flip(make_steps: MakeSteps) -> None:
    c = case(kind="steady")
    assert not score_case(c, make_steps(("cancel_order", ()), ("order_status", ()))).passed
