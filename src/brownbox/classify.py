"""Stage 6: the router. Reads a conversation one customer message at a time.

After each customer message the model gives the intent (or "unclear" / "other") and any
guards. What happens next, the routing decision, is a plain lookup in code: guards win,
then hand-off intents, then "ask to clarify", then the intent's agent. The model never
decides whether the AI may take part.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, create_model

from brownbox import llm
from brownbox.models import Conversation
from brownbox.ontology import Ontology
from brownbox.parse import cut_after_customer_message
from brownbox.prompts import format_conversation, render_ontology

ROUTER_MODEL = "claude-haiku-4-5"
OTHER = "other"
UNCLEAR = "unclear"

ROUTER_INSTRUCTIONS = """You route customer support conversations for BrownBox, an online \
retailer. You see the conversation so far, up to the customer's latest message.

- intent: the intent id the customer currently wants handled. Use "unclear" if they haven't \
said enough yet (e.g. "I have a question about my order"), and "other" if no intent fits.
- If a current intent is given, keep it unless the customer's latest message clearly changes \
what they want. Follow-up questions about the same request do not change it.
- guards: every guard that applies to anything the customer has said so far. Usually none."""


class Step(BaseModel):
    """The router's view after one customer message."""

    message: int
    intent: str
    guards: tuple[str, ...]


@dataclass(frozen=True)
class Routing:
    """The router's steps through one conversation, and the API usage behind each step."""

    steps: list[Step]
    usage: list[llm.Usage]


Outcome = Literal["specialist", "human", "clarify", "agent"]


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    reason: str
    agent: str | None = None
    signoff_actions: tuple[str, ...] = ()


def router_schema(ontology: Ontology) -> type[BaseModel]:
    intents = [*(i.id for i in ontology.intents), OTHER, UNCLEAR]
    guard = create_model("GuardOut", guard=(str, llm.one_of([g.id for g in ontology.guards])))
    return create_model(
        "RouterOutput",
        intent=(str, llm.one_of(intents)),
        guards=(list[guard], Field(description="Guards that apply so far; usually empty")),
    )


def router_system(ontology: Ontology, examples: dict[int, Conversation]) -> str:
    return ROUTER_INSTRUCTIONS + "\n\n" + render_ontology(ontology, examples)


def route_conversation(
    conv: Conversation,
    system: str,
    schema: type[BaseModel],
    model: str = ROUTER_MODEL,
    effort: llm.Effort | None = None,
    run: int = 0,
    upto: int | None = None,
) -> Routing:
    """Classify after each customer message (up to `upto`), carrying the current intent."""
    n = sum(t.role == "customer" for t in conv.turns)
    steps: list[Step] = []
    usage: list[llm.Usage] = []
    current: str | None = None
    for k in range(1, min(n, upto or n) + 1):
        prefix = Conversation(
            id=conv.id, split=conv.split, turns=tuple(cut_after_customer_message(conv.turns, k))
        )
        user = format_conversation(prefix, numbered=True)
        if current and current != UNCLEAR:
            user += f"\n\nCurrent intent so far: {current}"
        req = llm.Request(
            model=model, system=system, user=user, max_tokens=512, effort=effort, run=run
        )
        reply = llm.structured(req, schema)
        raw = reply.output.model_dump(mode="json")
        current = raw["intent"]
        steps.append(
            Step(
                message=k, intent=current, guards=tuple(sorted({g["guard"] for g in raw["guards"]}))
            )
        )
        usage.append(reply.usage)
    return Routing(steps, usage)


def decide(ontology: Ontology, steps: list[Step]) -> Decision:
    """The routing decision after the latest step. Guards are sticky: once fired, always fired."""
    fired = {g for step in steps for g in step.guards}
    guards = {g.id: g for g in ontology.guards}
    if any(guards[g].participation == "never" for g in fired):
        return Decision("specialist", f"guard: {', '.join(sorted(fired))}")
    if fired:
        return Decision("human", f"guard: {', '.join(sorted(fired))}")
    intent_id = steps[-1].intent
    if intent_id == UNCLEAR:
        return Decision("clarify", "not enough said yet")
    if intent_id == OTHER:
        return Decision("human", "no intent fits")
    intent = next(i for i in ontology.intents if i.id == intent_id)
    if intent.participation != "ai":
        return Decision("human", f"{intent.name} is a {intent.participation} intent")
    return Decision("agent", intent.name, intent.agent, tuple(intent.signoff_actions))
