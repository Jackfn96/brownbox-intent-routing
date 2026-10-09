"""Metrics for the router against labelled conversations. No API calls.

What the label expects at customer message k:
- before `clear_at`: nothing is scored (the customer hasn't said what they want yet);
- from `clear_at`: the primary intent, or the second request (the label doesn't record when
  the customer raises it, so either counts);
- from `switch_at`: the intent they switched to.

A label with the same intent as both second request and switch means a second request raised
at `switch_at` while the first is still live: before it only the primary counts, from it either
does, and it is not a switch (nothing was abandoned).

Every rate has a 95% interval. Shares of conversations use the Wilson score interval;
per-message rates use a bootstrap that resamples whole conversations, because messages within
one conversation aren't independent.

Per-intent precision and recall are measured at the message where the intent becomes clear, one
prediction per conversation. Most intents have only a handful of labelled conversations, so read
them as where to look, not as precise rates: the intervals say how little they pin down.
"""

import math
import random
from collections import Counter

from pydantic import BaseModel
from sklearn.metrics import cohen_kappa_score

from brownbox.classify import Step
from brownbox.models import GoldLabel
from brownbox.ontology import UNCLEAR

DRAWS = 2000
SEED = 0
Z = 1.96  # 95% interval.


class Rate(BaseModel):
    hits: int
    total: int
    value: float
    low: float  # 95% interval
    high: float


class ConversationScore(BaseModel):
    id: int
    mode: str  # How the label was made: blind, assisted or silver.
    expected: str  # The labelled primary intent.
    at_clear: str  # The router's intent at the message where the label says it's clear.
    correct_at_clear: bool
    agent_correct_at_clear: bool  # Right agent, even if the intent is wrong.
    messages_scored: int
    messages_correct: int
    final_correct: bool
    false_switches: int  # Router left a right intent while the request stayed the same.
    switch_delay: int | None  # Messages after a real switch until the router followed.
    switch_missed: bool
    guards_expected: dict[str, int]  # Guard -> message where it should first fire.
    guards_fired: dict[str, int]  # Guard -> message where the router first fired it.


class GuardCounts(BaseModel):
    expected: int  # Conversations where the label has this guard.
    fired: int  # Conversations where the router fired it.
    caught: int  # Both.
    delays: list[int]  # Fired message minus expected message, for each caught one.
    recall: Rate  # Of the conversations that should fire it, the share where it did.
    precision: Rate  # Of the conversations where it fired, the share that should have.
    flag_rate: Rate  # Share of all conversations where it fired.


class IntentStats(BaseModel):
    support: int  # Conversations labelled with this intent.
    predicted: int  # Conversations the router gave this intent at the clear message.
    recall: Rate
    precision: Rate
    f1: float | None  # None while the intent has no examples or was never predicted.


class Confusion(BaseModel):
    expected: str
    got: str
    count: int
    same_agent: bool  # The router still reached the right agent.


def added_request(label: GoldLabel) -> bool:
    """A second request raised at `switch_at`, with the first still live (not a switch)."""
    return label.secondary is not None and label.secondary == label.switch_to


def acceptable(label: GoldLabel, message: int) -> set[str] | None:
    """The intents that count as right at this customer message; None if not scored."""
    if message < label.clear_at:
        return None
    if label.switch_at is not None and label.switch_to is not None and message >= label.switch_at:
        return {label.switch_to} | ({label.primary} if added_request(label) else set())
    if label.secondary and not added_request(label):
        return {label.primary, label.secondary}
    return {label.primary}


def score_conversation(
    label: GoldLabel, steps: list[Step], agent_of: dict[str, str]
) -> ConversationScore:
    expected_at = {s.message: acceptable(label, s.message) for s in steps}
    scored = [s.message for s in steps if expected_at[s.message] is not None]
    right = {s.message for s in steps if s.intent in (expected_at[s.message] or set())}
    at_clear = next(s.intent for s in steps if s.message == label.clear_at)

    false_switches = sum(
        1
        for before, after in zip(scored, scored[1:], strict=False)
        if expected_at[before] == expected_at[after] and before in right and after not in right
    )
    switch_at = None if added_request(label) else label.switch_at  # A real switch, if any.
    switch_delay = None
    if switch_at is not None:
        followed = sorted(m for m in right if m >= switch_at)
        switch_delay = followed[0] - switch_at if followed else None

    fired: dict[str, int] = {}
    for s in steps:
        for g in s.guards:
            fired.setdefault(g, s.message)

    return ConversationScore(
        id=label.id,
        mode=label.mode,
        expected=label.primary,
        at_clear=at_clear,
        correct_at_clear=at_clear == label.primary,
        # "other" and "unclear" have no agent: each only matches itself.
        agent_correct_at_clear=agent_of.get(at_clear, at_clear)
        == agent_of.get(label.primary, label.primary),
        messages_scored=len(scored),
        messages_correct=len(right),
        final_correct=steps[-1].message in right,
        false_switches=false_switches,
        switch_delay=switch_delay,
        switch_missed=switch_at is not None and switch_delay is None,
        guards_expected=label.guards,
        guards_fired=fired,
    )


def rate(hits: list[int], totals: list[int], draws: int = DRAWS, seed: int = SEED) -> Rate:
    """sum(hits) / sum(totals) over conversations, with a bootstrap interval from resampling
    the conversations. For per-message rates, where a conversation contributes many messages."""
    rng = random.Random(seed)
    n = len(hits)
    samples = []
    for _ in range(draws):
        picks = [rng.randrange(n) for _ in range(n)]
        total = sum(totals[i] for i in picks)
        if total:
            samples.append(sum(hits[i] for i in picks) / total)
    samples.sort()
    return Rate(
        hits=sum(hits),
        total=sum(totals),
        value=sum(hits) / sum(totals),
        low=samples[int(0.025 * len(samples))],
        high=samples[int(0.975 * len(samples)) - 1],
    )


def share(flags: list[bool]) -> Rate:
    """The share of conversations where a flag is true, with a Wilson score interval.

    Unlike the bootstrap, Wilson gives a real interval at 0% and 100% (25/25 is not "certainly
    100%"). With nothing to count, the interval is the whole range.
    """
    n, hits = len(flags), sum(flags)
    if n == 0:
        return Rate(hits=0, total=0, value=0.0, low=0.0, high=1.0)
    p = hits / n
    centre = (p + Z**2 / (2 * n)) / (1 + Z**2 / n)
    half = Z * math.sqrt(p * (1 - p) / n + Z**2 / (4 * n**2)) / (1 + Z**2 / n)
    return Rate(
        hits=hits, total=n, value=p, low=max(0.0, centre - half), high=min(1.0, centre + half)
    )


def kappa(scores: list[ConversationScore]) -> float:
    """Cohen's kappa between labels and router at the clear message: agreement beyond chance."""
    return float(cohen_kappa_score([s.expected for s in scores], [s.at_clear for s in scores]))


def guard_counts(scores: list[ConversationScore], guards: list[str]) -> dict[str, GuardCounts]:
    counts = {}
    for g in guards:
        expected = [s for s in scores if g in s.guards_expected]
        fired = [s for s in scores if g in s.guards_fired]
        caught = [s for s in expected if g in s.guards_fired]
        counts[g] = GuardCounts(
            expected=len(expected),
            fired=len(fired),
            caught=len(caught),
            delays=[s.guards_fired[g] - s.guards_expected[g] for s in caught],
            recall=share([g in s.guards_fired for s in expected]),
            precision=share([g in s.guards_expected for s in fired]),
            flag_rate=share([g in s.guards_fired for s in scores]),
        )
    return counts


def per_intent(scores: list[ConversationScore]) -> dict[str, IntentStats]:
    """Precision, recall and F1 per intent at the clear message, for every intent that was
    either labelled or predicted, most-labelled first. "Unclear" is an outcome, never a label,
    so it has no row: answering it only lowers the true intent's recall."""
    intents = ({s.expected for s in scores} | {s.at_clear for s in scores}) - {UNCLEAR}
    stats = {}
    for i in intents:
        recall = share([s.at_clear == i for s in scores if s.expected == i])
        precision = share([s.expected == i for s in scores if s.at_clear == i])
        stats[i] = IntentStats(
            support=recall.total,
            predicted=precision.total,
            recall=recall,
            precision=precision,
            f1=f1(recall, precision),
        )
    return dict(sorted(stats.items(), key=lambda kv: (-kv[1].support, kv[0])))


def f1(recall: Rate, precision: Rate) -> float | None:
    """Harmonic mean of the two; None unless both were measured."""
    if not (recall.total and precision.total):
        return None
    total = recall.value + precision.value
    return 2 * recall.value * precision.value / total if total else 0.0


def confusions(scores: list[ConversationScore]) -> list[Confusion]:
    """Which intent the router gave instead of the labelled one, most frequent first."""
    pairs = Counter(
        (s.expected, s.at_clear, s.agent_correct_at_clear) for s in scores if not s.correct_at_clear
    )
    return [
        Confusion(expected=e, got=g, count=n, same_agent=a) for (e, g, a), n in pairs.most_common()
    ]


class LabelQuality(BaseModel):
    """How far to trust the labels, from comparing mine with the pre-labelling models."""

    blind_primary: Rate  # My blind labels vs the models, where the models fully agree.
    audit_primary: Rate  # My assisted labels vs the models, on the random audit.
    audit_full: Rate  # The same audit, every field: how far to trust the silver labels.


def label_quality(human: dict[int, GoldLabel], silver: dict[int, GoldLabel]) -> LabelQuality:
    """Blind vs audit is the anchoring check: both are random samples where the models fully
    agree, and the only difference is whether I saw their suggestion."""
    both = [i for i in human if i in silver]
    blind = [i for i in both if human[i].mode == "blind"]
    audit = [i for i in both if human[i].mode == "assisted"]
    fields = {"primary", "secondary", "clear_at", "switch_at", "switch_to", "guards"}

    def same(i: int) -> bool:
        return human[i].model_dump(include=fields) == silver[i].model_dump(include=fields)

    return LabelQuality(
        blind_primary=share([human[i].primary == silver[i].primary for i in blind]),
        audit_primary=share([human[i].primary == silver[i].primary for i in audit]),
        audit_full=share([same(i) for i in audit]),
    )
