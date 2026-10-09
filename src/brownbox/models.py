"""Core data types shared across the pipeline."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Role = Literal["customer", "staff"]
Split = Literal["dev", "practice", "locked", "synthetic"]  # synthetic: hand-written test cases.


class Turn(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Role
    speaker: str  # Original label, e.g. "Agent", "Supervisor", "Billing Team Agent".
    text: str


class Conversation(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    split: Split
    turns: tuple[Turn, ...]


class GoldLabel(BaseModel):
    """One hand label. Intent ids are checked against the ontology by the labelling tool."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    primary: str  # The first thing the customer wants done: an intent id, or "other".
    secondary: str | None = None  # A second, separate request, if any.
    clear_at: int = Field(ge=1)  # Customer message where the intent becomes clear.
    switch_at: int | None = Field(default=None, ge=2)  # Customer message where they change request.
    switch_to: str | None = None
    guards: dict[str, int] = {}  # Guard id -> customer message where it should first fire.
    note: str | None = None  # Why this one is an edge case, for review after labelling.
    # blind: labelled with no model suggestion; assisted: with one; synthetic: a hand-written
    # case; silver: not hand-labelled, both pre-labelling models gave this exact label.
    mode: Literal["blind", "assisted", "synthetic", "silver"]
    ontology_version: str

    @model_validator(mode="after")
    def check_switch(self) -> Self:
        if (self.switch_at is None) != (self.switch_to is None):
            raise ValueError("switch_at and switch_to go together")
        return self


class Adjudication(BaseModel):
    """A label corrected after review. The original stays as it was, because the blind and
    audit checks measure the labels as first made."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: GoldLabel
    reason: str


class Proposal(BaseModel):
    """A label suggested by a pre-labelling model, checked against the ontology on return."""

    model_config = ConfigDict(frozen=True)

    primary: str
    secondary: str | None
    clear_at: int = Field(ge=1)
    switch_at: int | None
    switch_to: str | None
    guards: dict[str, int]


class PreLabel(Proposal):
    """One model's proposal for one conversation, as stored in data/gold/prelabels.jsonl."""

    id: int
    model: str
    ontology_version: str  # The version the model was shown.
