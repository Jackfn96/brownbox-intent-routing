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
    mode: Literal["blind", "assisted", "synthetic"]
    ontology_version: str

    @model_validator(mode="after")
    def check_switch(self) -> Self:
        if (self.switch_at is None) != (self.switch_to is None):
            raise ValueError("switch_at and switch_to go together")
        return self
