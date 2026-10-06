"""The intent ontology: ontology/ontology.yaml, validated on load.

The YAML is the single source of truth. The classifier's prompt and the readable
ONTOLOGY.md are generated from it, so a typo or a dangling reference fails here,
not halfway through a run.
"""

from collections import Counter
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from brownbox.parse import load
from brownbox.paths import ROOT

ONTOLOGY = ROOT / "ontology" / "ontology.yaml"

# Outcomes the classifier can return that are not intents.
RESERVED_IDS = {"other", "unclear"}

Id = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
# Who runs the conversation: the AI, a person (emotional, relationship or legal risk), or
# nobody automated at all (security). Risky *actions* inside an AI intent are listed in
# signoff_actions: the AI prepares them and a person approves (decisions D13 and P6).
Participation = Literal["ai", "handoff", "never"]


class _Strict(BaseModel):
    """Unknown fields are errors, so a misspelt key can't be silently ignored."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Domain(_Strict):
    id: Id
    name: str


class Intent(_Strict):
    id: Id
    name: str
    domain: Id
    definition: str
    includes: list[str] = Field(min_length=1)
    excludes: list[str] = []
    # Nearest neighbour intent id -> how to tell this intent apart from it.
    boundaries: dict[Id, str] = {}
    # DEV conversation ids only: these become few-shot examples in the classifier prompt.
    examples: list[int] = Field(min_length=2)
    kind: Literal["inform", "act"]
    requires_verification: bool
    participation: Participation
    # Money moving outside standard policy, or anything hard to undo (policy-based money rule).
    signoff_actions: list[str] = []
    # What the fraud guard and the procedure's risk checks should watch for in this intent.
    fraud_signals: list[str] = []
    agent: Id  # Several intents can share one agent (decision D1).


class Guard(_Strict):
    """A yes/no check run on every customer message. When it fires it overrides the intent."""

    id: Id
    name: str
    definition: str
    fires_on: list[str] = Field(min_length=1)
    not_on: list[str] = Field(min_length=1)  # Near misses that must NOT fire it.
    participation: Literal["handoff", "never"]


class Ontology(_Strict):
    version: str
    domains: list[Domain]
    intents: list[Intent]
    guards: list[Guard]

    @model_validator(mode="after")
    def check_references(self) -> Self:
        problems = []
        ids = [
            *(d.id for d in self.domains),
            *(i.id for i in self.intents),
            *(g.id for g in self.guards),
        ]
        problems += [f"duplicate id: {i}" for i, n in Counter(ids).items() if n > 1]
        problems += [f"reserved id: {i}" for i in RESERVED_IDS.intersection(ids)]

        domains = {d.id for d in self.domains}
        intents = {i.id for i in self.intents}
        for intent in self.intents:
            if intent.domain not in domains:
                problems.append(f"{intent.id}: unknown domain {intent.domain}")
            for other in intent.boundaries:
                if other == intent.id or other not in intents:
                    problems.append(f"{intent.id}: boundary with unknown intent {other}")
        if problems:
            raise ValueError("; ".join(problems))
        return self


def load_ontology(path: Path = ONTOLOGY) -> Ontology:
    return Ontology.model_validate(yaml.safe_load(path.read_text()))


def non_dev_examples(ontology: Ontology, dev_ids: set[int]) -> list[str]:
    """Examples that aren't DEV conversations. They would leak held-out data into the prompt."""
    return [
        f"{intent.id}: #{conv_id}"
        for intent in ontology.intents
        for conv_id in intent.examples
        if conv_id not in dev_ids
    ]


def main() -> None:
    ontology = load_ontology()
    leaks = non_dev_examples(ontology, {c.id for c in load("dev")})
    if leaks:
        raise SystemExit(f"examples outside DEV: {', '.join(leaks)}")
    by_level = Counter(i.participation for i in ontology.intents)
    with_signoff = sum(bool(i.signoff_actions) for i in ontology.intents)
    print(
        f"ontology v{ontology.version} is valid: {len(ontology.domains)} domains, "
        f"{len(ontology.intents)} intents, {len(ontology.guards)} guards, "
        f"{len({i.agent for i in ontology.intents})} agents"
    )
    print(f"participation: {dict(sorted(by_level.items()))}; {with_signoff} with sign-off actions")


if __name__ == "__main__":
    main()
