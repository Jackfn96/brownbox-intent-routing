"""Score the router.

    uv run python -m brownbox.evaluate cases               # the hand-written cases
    uv run python -m brownbox.evaluate practice            # practice, my labels only
    uv run python -m brownbox.evaluate practice --silver   # plus the silver labels
    uv run python -m brownbox.evaluate practice --model claude-sonnet-5-5 --effort low
    uv run python -m brownbox.evaluate locked              # the final score, router frozen
    uv run python -m brownbox.evaluate guards              # guard precision/recall, all sets

Cases check what each was designed to test: does each guard fire, and how many messages late;
do traps stay silent; does the router follow a real switch and hold steady through follow-ups.
Practice and locked measure how often the router is right, with intervals, and what it costs;
practice also measures how far to trust the labels (see score.py). The locked set is scored only
with the router frozen, never to tune it. Results are saved to results/eval/; `guards` pools the
saved results, because each set alone has only a few conversations where a guard should fire.
"""

import argparse
from collections import Counter
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel

from brownbox import llm
from brownbox.cases import Case, load_cases
from brownbox.classify import (
    ROUTER_MODEL,
    Routing,
    Step,
    load_router_prompts,
    route_conversation,
)
from brownbox.label import (
    ADJUDICATED,
    LOCKED_LABELS,
    PRACTICE_LABELS,
    PRELABELS,
    load_adjudicated,
    load_labels,
    load_suggestions,
)
from brownbox.models import Conversation, GoldLabel
from brownbox.ontology import OTHER, UNCLEAR, Ontology, load_ontology
from brownbox.parse import load
from brownbox.paths import RESULTS
from brownbox.score import (
    Confusion,
    ConversationScore,
    GuardCounts,
    IntentStats,
    LabelQuality,
    Rate,
    confusions,
    guard_counts,
    kappa,
    label_quality,
    per_intent,
    rate,
    score_conversation,
    share,
)

EVAL_DIR = RESULTS / "eval"
EvalSet = Literal["cases", "practice", "locked"]


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


class Report(BaseModel):
    split: EvalSet
    ontology_version: str | None = None  # None: saved before the version was recorded.
    model: str
    effort: llm.Effort | None
    labels: str  # Which labels: "hand-written" (cases), "mine" or "mine+silver".
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
    label_quality: LabelQuality | None  # Practice only: there are no model labels for locked.
    per_intent: dict[str, IntentStats]  # At the clear message; few examples per intent.
    confusions: list[Confusion]
    by_conversation: list[ConversationScore]


def route_all(
    convs: list[Conversation], ontology: Ontology, model: str, effort: llm.Effort | None
) -> list[Routing]:
    prompts = load_router_prompts(ontology)
    print(f"routing {len(convs)} conversations with {model}...", flush=True)
    return llm.run_all(
        lambda c: route_conversation(c, prompts, model, effort), convs, "conversations"
    )


def build_report(
    split: EvalSet,
    convs: list[Conversation],
    labels: dict[int, GoldLabel],
    label_set: str,
    quality: LabelQuality | None,
    routings: list[Routing],
    ontology: Ontology,
    model: str,
    effort: llm.Effort | None,
) -> Report:
    agent_of = {i.id: i.agent for i in ontology.intents}
    scores = [
        score_conversation(labels[c.id], r.steps, agent_of)
        for c, r in zip(convs, routings, strict=True)
    ]
    usage = [u for r in routings for u in r.usage]
    switched = [s for s in scores if s.switch_delay is not None or s.switch_missed]
    quiet = [s for s in scores if not s.guards_expected]

    return Report(
        split=split,
        ontology_version=ontology.version,
        model=model,
        effort=effort,
        labels=label_set,
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
        label_quality=quality,
        per_intent=per_intent(scores),
        confusions=confusions(scores),
        by_conversation=scores,
    )


def run_cases(model: str, effort: llm.Effort | None) -> Report:
    ontology = load_ontology()
    cases = load_cases(ontology)
    convs = [c.conversation() for c in cases]
    routings = route_all(convs, ontology, model, effort)
    results = [score_case(c, r.steps) for c, r in zip(cases, routings, strict=True)]

    print(f"\nRouter {model} on {len(results)} hand-written cases\n")
    by_kind = Counter(r.kind for r in results)
    passed = Counter(r.kind for r in results if r.passed)
    for kind in sorted(by_kind):
        print(f"  {kind:7} {passed[kind]}/{by_kind[kind]} passed")
    print(f"  {'total':7} {sum(passed.values())}/{len(results)}\n")
    for r in results:
        if not r.passed:
            print(f"  #{r.id} {r.kind}: {r.detail}")

    labels = {c.id: c.label(ontology.version) for c in cases}
    return build_report(
        "cases", convs, labels, "hand-written", None, routings, ontology, model, effort
    )


def run_practice(model: str, effort: llm.Effort | None, with_silver: bool) -> Report:
    original = load_labels(PRACTICE_LABELS)
    mine = original | load_adjudicated(ADJUDICATED)  # Score against corrected labels.
    silver = load_suggestions(PRELABELS).agreed
    labels: dict[int, GoldLabel] = (silver | mine) if with_silver else mine
    by_id = {c.id: c for c in load("practice")}
    quality = label_quality(original, silver)  # Labels as first made.
    label_set = "mine+silver" if with_silver else "mine"
    convs = [by_id[i] for i in sorted(labels)]
    ontology = load_ontology()
    routings = route_all(convs, ontology, model, effort)
    return build_report(
        "practice", convs, labels, label_set, quality, routings, ontology, model, effort
    )


def run_locked(model: str, effort: llm.Effort | None) -> Report:
    """The final score: my blind labels on the locked set, whatever has been labelled so far.

    It only scores the ontology version the labels were made with. The locked set scores one
    frozen version once; a later version was shaped by its errors, so it can't be tested on it.
    """
    labels = load_labels(LOCKED_LABELS)
    if not labels:
        raise SystemExit("no locked labels yet: run `make label-locked` first")
    ontology = load_ontology()
    labelled = {label.ontology_version for label in labels.values()}
    if labelled != {ontology.version}:
        raise SystemExit(
            f"the locked set was labelled against ontology v{', v'.join(sorted(labelled))}; "
            f"scoring v{ontology.version} on it would use the test set twice"
        )
    by_id = {c.id: c for c in load("locked", unlock=True)}
    convs = [by_id[i] for i in sorted(labels)]
    routings = route_all(convs, ontology, model, effort)
    return build_report("locked", convs, labels, "mine", None, routings, ontology, model, effort)


def percent(r: Rate) -> str:
    if not r.total:
        return "   –"
    return f"{r.value:4.0%} ({r.hits}/{r.total})  95% CI {r.low:.0%}–{r.high:.0%}"


def guard_table(guards: dict[str, GuardCounts]) -> list[str]:
    lines = ["  Guard                   recall                        precision"]
    for g, c in guards.items():
        if c.expected or c.fired:
            lines.append(f"    {g:22}{percent(c.recall):30}{percent(c.precision)}")
            lines.append(f"    {'':22}flag rate {c.flag_rate.value:.0%}; messages late: {c.delays}")
    return lines


def intent_table(stats: dict[str, IntentStats]) -> list[str]:
    lines = [
        "  Per intent at the clear message. Few examples each: read as where to look.",
        f"    {'intent':26}{'n':>3}{'pred':>5}  {'recall':>8}  {'precision':>9}  {'F1':>4}",
    ]
    for i, s in stats.items():
        recall = f"{s.recall.value:.0%}" if s.recall.total else "–"
        precision = f"{s.precision.value:.0%}" if s.precision.total else "–"
        f1 = f"{s.f1:.2f}" if s.f1 is not None else "–"
        lines.append(
            f"    {i:26}{s.support:>3}{s.predicted:>5}  {recall:>8}  {precision:>9}  {f1:>4}"
        )
    return lines


def print_report(report: Report) -> None:
    lines = [
        f"\nRouter {report.model} (effort {report.effort or 'default'}) on "
        f"{report.conversations} {report.split} conversations, labels: {report.labels}\n",
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
        "",
        *guard_table(report.guards),
    ]
    if q := report.label_quality:
        lines += [
            "\n  Labels (mine vs the pre-labelling models, where both models fully agree)",
            f"    Blind, intent                     {percent(q.blind_primary)}",
            f"    Audit, intent                     {percent(q.audit_primary)}",
            f"    Audit, every field                {percent(q.audit_full)}",
        ]
    lines += [
        f"\n  Cost ${report.cost_usd:.2f} for {report.calls} calls "
        f"(${report.cost_usd / report.conversations:.4f} per conversation), "
        f"mean latency {report.mean_latency_s:.1f}s per call",
        "",
        *intent_table(report.per_intent),
        "\n  Confusions at the clear message (labelled → router):",
    ]
    lines += [
        f"    {c.count} × {c.expected} → {c.got}" + (" (same agent)" if c.same_agent else "")
        for c in report.confusions
    ]
    print("\n".join(lines))


def report_path(split: EvalSet, labels: str, model: str, effort: llm.Effort | None) -> Path:
    return EVAL_DIR / f"{split}-{labels}-{model}-{effort or 'default'}.json"


def save(report: Report) -> Path:
    path = report_path(report.split, report.labels, report.model, report.effort)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2))
    return path


def run_guards(model: str, effort: llm.Effort | None) -> None:
    """Guard precision and recall from the saved reports, per set and pooled."""
    sets: list[tuple[EvalSet, str]] = [
        ("cases", "hand-written"),
        ("practice", "mine"),
        ("locked", "mine"),
    ]
    reports = []
    for split, labels in sets:
        path = report_path(split, labels, model, effort)
        if not path.exists():
            raise SystemExit(f"no saved {split} results for {model}: run `evaluate {split}` first")
        reports.append(Report.model_validate_json(path.read_text()))
    ontology = load_ontology()
    for r in reports:
        version = f"v{r.ontology_version}" if r.ontology_version else "version not recorded"
        print(f"\n{r.split} ({r.conversations} conversations, ontology {version})")
        print("\n".join(guard_table(r.guards)))
    # Pool only sets scored on the current ontology: mixing versions would blur both.
    current = [r for r in reports if r.ontology_version == ontology.version]
    pooled = [s for r in current for s in r.by_conversation]
    names = " + ".join(r.split for r in current)
    print(f"\nPooled on ontology v{ontology.version}: {names} ({len(pooled)} conversations)")
    print("\n".join(guard_table(guard_counts(pooled, [g.id for g in ontology.guards]))))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("set", choices=[*get_args(EvalSet), "guards"])
    parser.add_argument("--model", default=ROUTER_MODEL, choices=sorted(llm.PRICES))
    parser.add_argument("--effort", choices=get_args(llm.Effort))
    parser.add_argument("--silver", action="store_true", help="also score the silver labels")
    args = parser.parse_args()

    if args.set == "guards":
        run_guards(args.model, args.effort)
        return
    if args.set == "cases":
        path = save(run_cases(args.model, args.effort))
    else:
        if args.set == "locked":
            report = run_locked(args.model, args.effort)
        else:
            report = run_practice(args.model, args.effort, args.silver)
        path = save(report)
        print_report(report)
    print(f"\nSaved {path.relative_to(RESULTS.parent)}")


if __name__ == "__main__":
    main()
