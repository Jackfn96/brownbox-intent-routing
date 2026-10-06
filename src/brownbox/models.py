"""Core data types shared across the pipeline."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Role = Literal["customer", "staff"]
Split = Literal["dev", "practice", "locked"]


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
