"""Stage 6: the router. Reads a conversation one customer message at a time.

After each customer message, one model call gives the intent (or "unclear" / "other") and
whether the message changes the request; a separate yes/no call per guard checks the message
against that guard alone. What happens next, the routing decision, is a plain lookup in code:
guards win, then hand-off intents, then "ask to clarify", then the intent's agent. The model
never decides whether the AI may take part.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, create_model

from brownbox import llm
from brownbox.models import Conversation
from brownbox.ontology import Guard, Ontology
from brownbox.parse import cut_after_customer_message
from brownbox.prompts import format_conversation, render_ontology

ROUTER_MODEL = "claude-haiku-4-5"
OTHER = "other"
UNCLEAR = "unclear"

ROUTER_INSTRUCTIONS = """You route customer support conversations for BrownBox, an online \
retailer. You see the conversation so far, up to the customer's latest message.

- intent: the intent id the customer wants handled now. Use "unclear" if they haven't said \
enough yet (e.g. "I have a question about my order"), and "other" if no intent fits. Guards \
are checked separately: when one applies, still give the closest intent.
- changes_request: only matters when a current intent is given. true if the latest message \
asks for something the current intent's procedure can't handle, or drops the current request \
for a different one ("actually, just cancel it instead"; "can you also send me an invoice?"). \
false for:
  - follow-up questions about the same request: timing, fees, steps, options or outcome \
("how long will the refund take?", "why is there a restocking fee?");
  - answers to the agent's questions ("yes", an order number, an address);
  - closing messages ("thanks", "that's all", "goodbye");
  - frustration about the same request ("that's ridiculous", "this is unacceptable")."""

GUARD_INSTRUCTIONS = """You check one rule on a customer support conversation for BrownBox, an \
online retailer. You see the conversation so far, up to the customer's latest message.

Decide whether the customer's latest message triggers the check below. Read the earlier \
conversation only as context: judge the latest message.

- quote: the customer's exact words in the latest message that trigger the check, or "" if \
nothing does.
- fires: true only if the quoted words match the check and are not one of its near misses."""


class Step(BaseModel):
    """The router's view after one customer message."""

    message: int
    intent: str
    guards: tuple[str, ...]  # Guards that first fired at this message.


@dataclass(frozen=True)
class Routing:
    """The router's steps through one conversation, and the API usage behind each call."""

    steps: list[Step]
    usage: list[llm.Usage]


class GuardCheck(BaseModel):
    quote: str = Field(description="The customer's words that trigger the check, or empty")
    fires: bool


@dataclass(frozen=True)
class RouterPrompts:
    """Everything the router sends: the intent prompt and its schema, and one prompt per guard."""

    system: str
    schema: type[BaseModel]
    guards: dict[str, str]  # Guard id -> that guard's system prompt.


Outcome = Literal["specialist", "human", "clarify", "agent"]


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    reason: str
    agent: str | None = None
    signoff_actions: tuple[str, ...] = ()


def router_schema(ontology: Ontology) -> type[BaseModel]:
    intents = [*(i.id for i in ontology.intents), OTHER, UNCLEAR]
    return create_model(
        "RouterOutput",
        intent=(str, llm.one_of(intents)),
        changes_request=(
            bool,
            Field(description="Does the latest message change what the customer wants handled?"),
        ),
    )


def guard_system(guard: Guard) -> str:
    lines = [GUARD_INSTRUCTIONS, "", f"Check: {guard.name}", guard.definition, "", "Fires on:"]
    lines += [f"- {example}" for example in guard.fires_on]
    lines += ["", "Near misses (does not fire):"]
    lines += [f"- {example}" for example in guard.not_on]
    return "\n".join(lines)


def router_prompts(ontology: Ontology, examples: dict[int, Conversation]) -> RouterPrompts:
    return RouterPrompts(
        system=ROUTER_INSTRUCTIONS + "\n\n" + render_ontology(ontology, examples),
        schema=router_schema(ontology),
        guards={g.id: guard_system(g) for g in ontology.guards},
    )


def route_conversation(
    conv: Conversation,
    prompts: RouterPrompts,
    model: str = ROUTER_MODEL,
    effort: llm.Effort | None = None,
    run: int = 0,
    upto: int | None = None,
) -> Routing:
    """Classify after each customer message (up to `upto`), carrying the current intent.

    Once there is a real intent, it only changes when the model says the latest message
    changes the request: the model judges the message, code decides whether to switch.
    Guards are sticky, so a guard that has fired is not checked again.
    """
    n = sum(t.role == "customer" for t in conv.turns)
    steps: list[Step] = []
    usage: list[llm.Usage] = []
    current = UNCLEAR  # Nothing said yet.
    fired: set[str] = set()
    for k in range(1, min(n, upto or n) + 1):
        prefix = Conversation(
            id=conv.id, split=conv.split, turns=tuple(cut_after_customer_message(conv.turns, k))
        )
        transcript = format_conversation(prefix, numbered=True)
        settled = current not in (UNCLEAR, OTHER)
        user = transcript + (f"\n\nCurrent intent so far: {current}" if settled else "")
        reply = llm.structured(
            llm.Request(model, prompts.system, user, max_tokens=512, effort=effort, run=run),
            prompts.schema,
        )
        usage.append(reply.usage)
        raw = reply.output.model_dump(mode="json")
        if not settled or raw["changes_request"]:
            current = raw["intent"]

        new_guards = []
        for guard, system in prompts.guards.items():
            if guard in fired:
                continue
            check = llm.structured(
                llm.Request(model, system, transcript, max_tokens=256, effort=effort, run=run),
                GuardCheck,
            )
            usage.append(check.usage)
            if check.output.fires:
                new_guards.append(guard)
        fired.update(new_guards)
        steps.append(Step(message=k, intent=current, guards=tuple(sorted(new_guards))))
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
