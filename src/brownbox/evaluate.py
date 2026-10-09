"""Stage 7: score the router.

    uv run python -m brownbox.evaluate cases               # the hand-written cases
    uv run python -m brownbox.evaluate practice            # practice, my labels only
    uv run python -m brownbox.evaluate practice --silver   # plus the silver labels
    uv run python -m brownbox.evaluate practice --model claude-sonnet-5-5 --effort low

Cases check what each was designed to test: does each guard fire, and how many messages late;
do traps stay silent; does the router follow a real switch and hold steady through follow-ups.
Practice measures how often the router is right, with intervals, what it costs, and how far to
trust the labels (see score.py). Practice results are saved to results/eval/.
"""

import argparse
from collections import Counter

from pydantic import BaseModel

from brownbox import llm
from brownbox.cases import Case, load_cases
from brownbox.classify import (
    OTHER,
    ROUTER_MODEL,
    UNCLEAR,
    Step,
    route_conversation,
    router_prompts,
)
from brownbox.label import (
    ADJUDICATED,
    PRACTICE_LABELS,
    PRELABELS,
    load_adjudicated,
    load_labels,
    load_suggestions,
)
from brownbox.models import GoldLabel
from brownbox.ontology import load_ontology
from brownbox.parse import load
from brownbox.paths import RESULTS
from brownbox.score import (
    ConversationScore,
    GuardCounts,
    LabelQuality,
    Rate,
    guard_counts,
    kappa,
    label_quality,
    rate,
    score_conversation,
    share,
)

EVAL_DIR = RESULTS / "eval"


class CaseResult(BaseModel):
    id: int
    kind: str
    passed: bool
    detail: str


def first_fired(steps: list[Step], guard: str) -> int | None:
    return next((s.message for s in steps if guard in s.guards), None)


def score_case(case: Case, steps: list[Step]) -> CaseResult:
    """Did the router do what this case is designed to test?"""
    at = {s.message: s.intent for s in steps}
    problems = []
    for guard, expected in case.guards.items():
        fired = first_fired(steps, guard)
        if fired is None:
            problems.append(f"{guard} never fired (expected C{expected})")
        elif fired != expected:
            problems.append(f"{guard} fired at C{fired}, expected C{expected}")
    unexpected = {g for s in steps for g in s.guards} - set(case.guards)
    problems += [f"{g} fired but shouldn't" for g in sorted(unexpected)]

    if not case.guards:  # Intent checks only matter when no guard takes over.
        if at.get(case.clear_at) != case.primary:
            problems.append(f"C{case.clear_at}: {at.get(case.clear_at)}, expected {case.primary}")
        if case.switch_at is not None:
            after = [at[m] for m in at if m >= case.switch_at]
            if case.switch_to not in after:
                problems.append(f"missed switch to {case.switch_to} at C{case.switch_at}")
        if case.kind == "steady":
            later = {at[m] for m in at if m >= case.clear_at}
            if later != {case.primary}:
                problems.append(f"flipped after C{case.clear_at}: {sorted(later)}")
    return CaseResult(
        id=case.id, kind=case.kind, passed=not problems, detail="; ".join(problems) or "ok"
    )


def run_cases(model: str, effort: llm.Effort | None) -> None:
    ontology = load_ontology()
    cases = load_cases(ontology)
    prompts = router_prompts(ontology, {c.id: c for c in load("dev")})
    runs = llm.run_all(
        lambda c: route_conversation(c.conversation(), prompts, model, effort).steps,
        cases,
        "cases",
    )
    results = [score_case(c, s) for c, s in zip(cases, runs, strict=True)]

    print(f"\nRouter {model} on {len(results)} hand-written cases\n")
    by_kind = Counter(r.kind for r in results)
    passed = Counter(r.kind for r in results if r.passed)
    for kind in sorted(by_kind):
        print(f"  {kind:7} {passed[kind]}/{by_kind[kind]} passed")
    print(f"  {'total':7} {sum(passed.values())}/{len(results)}\n")
    for r in results:
        if not r.passed:
            print(f"  #{r.id} {r.kind}: {r.detail}")


class PracticeReport(BaseModel):
    model: str
    effort: str | None
    labels: str  # Which labels were scored against: "mine" or "mine+silver".
    conversations: int
    intent_at_clear: Rate
    agent_at_clear: Rate
    messages: Rate  # Every scored customer message.
    final_message: Rate
    kappa: float
    unclear_at_clear: int
    other_at_clear: int
    false_switches: Rate  # Conversations where the router left a right intent for no reason.
    switches: int
    switches_missed: int
    switch_delays: list[int]
    guards: dict[str, GuardCounts]
    false_alarms: Rate  # Conversations with no expected guard where the router fired one.
    calls: int
    cost_usd: float
    mean_latency_s: float
    label_quality: LabelQuality
    by_conversation: list[ConversationScore]


def run_practice(model: str, effort: llm.Effort | None, with_silver: bool) -> PracticeReport:
    ontology = load_ontology()
    original = load_labels(PRACTICE_LABELS)
    mine = original | load_adjudicated(ADJUDICATED)  # Score against corrected labels.
    silver = load_suggestions(PRELABELS, ontology.version).agreed
    labels: dict[int, GoldLabel] = (silver | mine) if with_silver else mine
    by_id = {c.id: c for c in load("practice")}
    convs = [by_id[i] for i in sorted(labels)]

    prompts = router_prompts(ontology, {c.id: c for c in load("dev")})
    print(f"routing {len(convs)} practice conversations with {model}...", flush=True)
    routings = llm.run_all(
        lambda c: route_conversation(c, prompts, model, effort), convs, "conversations"
    )
    agent_of = {i.id: i.agent for i in ontology.intents}
    scores = [
        score_conversation(labels[c.id], r.steps, agent_of)
        for c, r in zip(convs, routings, strict=True)
    ]
    usage = [u for r in routings for u in r.usage]
    switched = [s for s in scores if s.switch_delay is not None or s.switch_missed]
    quiet = [s for s in scores if not s.guards_expected]

    return PracticeReport(
        model=model,
        effort=effort,
        labels="mine+silver" if with_silver else "mine",
        conversations=len(scores),
        intent_at_clear=share([s.correct_at_clear for s in scores]),
        agent_at_clear=share([s.agent_correct_at_clear for s in scores]),
        messages=rate([s.messages_correct for s in scores], [s.messages_scored for s in scores]),
        final_message=share([s.final_correct for s in scores]),
        kappa=kappa(scores),
        unclear_at_clear=sum(s.at_clear == UNCLEAR for s in scores),
        other_at_clear=sum(s.at_clear == OTHER for s in scores),
        false_switches=share([s.false_switches > 0 for s in scores]),
        switches=len(switched),
        switches_missed=sum(s.switch_missed for s in switched),
        switch_delays=[s.switch_delay for s in switched if s.switch_delay is not None],
        guards=guard_counts(scores, [g.id for g in ontology.guards]),
        false_alarms=share([bool(s.guards_fired) for s in quiet]),
        calls=len(usage),
        cost_usd=sum(llm.cost(u, model) for u in usage),
        mean_latency_s=sum(u.latency_s for u in usage) / len(usage),
        label_quality=label_quality(original, silver),  # Labels as first made.
        by_conversation=scores,
    )


def percent(r: Rate) -> str:
    return f"{r.value:4.0%} ({r.hits}/{r.total})  95% CI {r.low:.0%}–{r.high:.0%}"


def print_practice(report: PracticeReport) -> None:
    q = report.label_quality
    lines = [
        f"\nRouter {report.model} (effort {report.effort or 'default'}) on "
        f"{report.conversations} practice conversations, labels: {report.labels}\n",
        f"  Intent right when it becomes clear  {percent(report.intent_at_clear)}",
        f"  Agent right when it becomes clear   {percent(report.agent_at_clear)}",
        f"  Every scored customer message       {percent(report.messages)}",
        f"  Last customer message               {percent(report.final_message)}",
        f"  Cohen's kappa at the clear message  {report.kappa:.2f}",
        f"  Unclear / other when it was clear   {report.unclear_at_clear} / "
        f"{report.other_at_clear}",
        f"  False switches                      {percent(report.false_switches)}",
        f"  Real switches                       {report.switches}, missed "
        f"{report.switches_missed}, messages to follow: {report.switch_delays}",
        f"  False alarms (guard, none expected) {percent(report.false_alarms)}",
        "  Guards: expected / fired / caught / delay in messages",
    ]
    lines += [
        f"    {g:22} {c.expected} / {c.fired} / {c.caught} / {c.delays}"
        for g, c in report.guards.items()
        if c.expected or c.fired
    ]
    lines += [
        "\n  Labels (mine vs the pre-labelling models, where both models fully agree)",
        f"    Blind, intent                     {percent(q.blind_primary)}",
        f"    Audit, intent                     {percent(q.audit_primary)}",
        f"    Audit, every field                {percent(q.audit_full)}",
        f"\n  Cost ${report.cost_usd:.2f} for {report.calls} calls "
        f"(${report.cost_usd / report.conversations:.4f} per conversation), "
        f"mean latency {report.mean_latency_s:.1f}s per call",
        "\n  Wrong when it became clear:",
    ]
    lines += [
        f"    #{s.id} ({s.mode}) expected {s.expected}, got {s.at_clear}"
        + (" (same agent)" if s.agent_correct_at_clear else "")
        for s in report.by_conversation
        if not s.correct_at_clear
    ]
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("set", choices=["cases", "practice"])
    parser.add_argument("--model", default=ROUTER_MODEL)
    parser.add_argument("--effort", choices=["low", "medium", "high"])
    parser.add_argument("--silver", action="store_true", help="also score the silver labels")
    args = parser.parse_args()

    if args.set == "cases":
        run_cases(args.model, args.effort)
        return
    report = run_practice(args.model, args.effort, args.silver)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    path = EVAL_DIR / f"practice-{report.labels}-{report.model}-{report.effort or 'default'}.json"
    path.write_text(report.model_dump_json(indent=2))
    print_practice(report)
    print(f"\nSaved {path.relative_to(RESULTS.parent)}")


if __name__ == "__main__":
    main()
