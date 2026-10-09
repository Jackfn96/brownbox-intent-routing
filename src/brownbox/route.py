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
    router_prompts,
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


def describe(steps: list[Step], decision: Decision, ontology: Ontology) -> str:
    names = {i.id: i.name for i in ontology.intents}
    latest = steps[-1]
    fired = sorted({g for s in steps for g in s.guards})  # Guards are sticky.
    lines = [
        f"C{latest.message}  intent: {names.get(latest.intent, latest.intent)}",
        f"    guards so far: {', '.join(fired) or 'none'}",
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
    prompts = router_prompts(ontology, {c.id: c for c in load("dev")})
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
        steps = route_conversation(conv, prompts, model=args.model).steps
        print(describe(steps, decide(ontology, steps), ontology))
        if args.show_prompt:
            print(f"\n--- system prompt ---\n{prompts.system}\n\n--- conversation ---")
            print(format_conversation(conv, numbered=True))


if __name__ == "__main__":
    main()
