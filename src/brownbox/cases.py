"""Hand-written test cases for what the data barely contains: guards and changes of request.

eval/cases.yaml holds short conversations with the label each should get. They are scored
separately from the gold set, and are never used to build or tune the ontology.
"""

from collections import Counter
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from brownbox.models import Conversation, GoldLabel, Turn
from brownbox.ontology import OTHER, Ontology, load_ontology
from brownbox.paths import ROOT

CASES = ROOT / "eval" / "cases.yaml"

# guard: a guard must fire. trap: a near miss where no guard may fire.
# switch: the customer abandons their first request. addon: they add a second one.
# steady: neither, e.g. a follow-up question or a vague opener (checks for false switches).
Kind = Literal["guard", "trap", "switch", "addon", "steady"]


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int = Field(ge=9000)  # Well clear of real conversation ids (0-999).
    kind: Kind
    note: str
    turns: tuple[tuple[Literal["customer", "agent"], str], ...]
    primary: str
    secondary: str | None = None
    clear_at: int = Field(default=1, ge=1)
    switch_at: int | None = Field(default=None, ge=2)
    switch_to: str | None = None
    guards: dict[str, int] = {}

    @model_validator(mode="after")
    def check_kind(self) -> Self:
        expected = {
            "guard": bool(self.guards),
            "trap": not self.guards,
            "switch": self.switch_at is not None,
            "addon": self.secondary is not None,
            "steady": self.switch_at is None and self.secondary is None,
        }
        if not expected[self.kind]:
            raise ValueError(f"case {self.id}: fields don't match kind {self.kind!r}")
        return self

    def customer_messages(self) -> int:
        return sum(role == "customer" for role, _ in self.turns)

    def conversation(self) -> Conversation:
        turns = tuple(
            Turn(role="customer" if role == "customer" else "staff", speaker=role.title(), text=t)
            for role, t in self.turns
        )
        return Conversation(id=self.id, split="synthetic", turns=turns)

    def label(self, ontology_version: str) -> GoldLabel:
        return GoldLabel(
            id=self.id,
            primary=self.primary,
            secondary=self.secondary,
            clear_at=self.clear_at,
            switch_at=self.switch_at,
            switch_to=self.switch_to,
            guards=self.guards,
            mode="synthetic",
            ontology_version=ontology_version,
        )


def problems(cases: list[Case], ontology: Ontology) -> list[str]:
    """Intent and guard ids must exist, and message numbers must be in range."""
    intents = {i.id for i in ontology.intents} | {OTHER}
    guards = {g.id for g in ontology.guards}
    found = [f"duplicate case id {i}" for i, n in Counter(c.id for c in cases).items() if n > 1]
    for c in cases:
        n = c.customer_messages()
        for field, value in [
            ("primary", c.primary),
            ("secondary", c.secondary),
            ("switch_to", c.switch_to),
        ]:
            if value is not None and value not in intents:
                found.append(f"case {c.id}: unknown {field} intent {value}")
        found += [f"case {c.id}: unknown guard {g}" for g in c.guards if g not in guards]
        messages = [c.clear_at, c.switch_at, *c.guards.values()]
        found += [
            f"case {c.id}: message {m} but only {n} customer messages"
            for m in messages
            if m is not None and m > n
        ]
    return found


def load_cases(ontology: Ontology, path: Path = CASES) -> list[Case]:
    cases = [Case.model_validate(c) for c in yaml.safe_load(path.read_text())]
    found = problems(cases, ontology)
    if found:
        raise ValueError("; ".join(found))
    return cases


def main() -> None:
    cases = load_cases(load_ontology())
    kinds = Counter(c.kind for c in cases)
    guards = Counter(g for c in cases for g in c.guards)
    late = sum(any(m > 1 for m in c.guards.values()) for c in cases)
    print(f"{len(cases)} cases are valid: {dict(sorted(kinds.items()))}")
    print(f"guards expected: {dict(sorted(guards.items()))}; {late} fire after the first message")


if __name__ == "__main__":
    main()
