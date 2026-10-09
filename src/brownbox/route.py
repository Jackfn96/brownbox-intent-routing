"""Try the router from the command line.

uv run route "I need some help with my account"   # one message
uv run route                                       # type a conversation, one message per line
uv run route --show-prompt "..."                   # also print exactly what the model saw
"""

import argparse

from brownbox.classify import (
    ROUTER_MODEL,
    Decision,
    Step,
    decide,
    route_conversation,
    router_schema,
    router_system,
)
from brownbox.models import Conversation, Turn
from brownbox.ontology import Ontology, load_ontology
from brownbox.parse import load
from brownbox.prompts import format_conversation

OUTCOME_TEXT = {
    "specialist": "Hand to the specialist team (never automated)",
    "human": "Hand to a person",
    "clarify": "Ask a clarifying question",
    "agent": "AI agent",
}


def describe(step: Step, decision: Decision, ontology: Ontology) -> str:
    names = {i.id: i.name for i in ontology.intents}
    lines = [
        f"C{step.message}  intent: {names.get(step.intent, step.intent)}",
        f"    guards: {', '.join(step.guards) or 'none'}",
        f"    → {OUTCOME_TEXT[decision.outcome]}: {decision.reason}"
        + (f" (agent {decision.agent})" if decision.agent else ""),
    ]
    lines += [f"      needs sign-off: {a}" for a in decision.signoff_actions]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Try the BrownBox router.")
    parser.add_argument("message", nargs="?", help="a single customer message")
    parser.add_argument("--model", default=ROUTER_MODEL)
    parser.add_argument("--show-prompt", action="store_true", help="print what the model saw")
    args = parser.parse_args()

    ontology = load_ontology()
    system = router_system(ontology, {c.id: c for c in load("dev")})
    schema = router_schema(ontology)
    turns: list[Turn] = []
    pending = [args.message] if args.message else None
    if pending is None:
        print("Type the customer's messages, one per line. Empty line to finish.")

    while True:
        text = pending.pop() if pending else (None if args.message else input("customer> "))
        if not text:
            break
        turns.append(Turn(role="customer", speaker="Customer", text=text))
        conv = Conversation(id=0, split="synthetic", turns=tuple(turns))
        steps = route_conversation(conv, system, schema, model=args.model).steps
        print(describe(steps[-1], decide(ontology, steps), ontology))
        if args.show_prompt:
            print(f"\n--- system prompt ---\n{system}\n\n--- conversation ---")
            print(format_conversation(conv, numbered=True))


if __name__ == "__main__":
    main()
