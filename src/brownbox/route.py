"""Try the router from the command line.

uv run route "I need some help with my account"   # one message
uv run route                                       # type a conversation, one message per line
uv run route --show-prompt "..."                   # also print the intent prompt and transcript
"""

import argparse
import readline  # noqa: F401  Imported for its side effect: line editing (backspace, arrows) in input().
from collections.abc import Iterable, Iterator

from pydantic import BaseModel, Field

from brownbox import llm
from brownbox.classify import (
    ROUTER_MODEL,
    Decision,
    Outcome,
    Step,
    decide,
    load_router_prompts,
    route_conversation,
)
from brownbox.models import Conversation, Turn
from brownbox.ontology import Ontology, load_ontology
from brownbox.prompts import format_conversation

GREETING = "Hi, I'm Alex from BrownBox customer support. How can I help you today?"
# The fixed question, if writing a targeted one fails.
CLARIFYING_QUESTION = "Of course. Could you tell me a bit more about what you need help with?"

# Demo only: when the router says "unclear", an agent would ask a question that tells the likely
# requests apart. This writes one. It isn't part of the router or the evaluation.
CLARIFY_INSTRUCTIONS = """You are Alex, a BrownBox customer support agent. The customer hasn't \
said enough yet to tell which of these requests they mean:

{intents}

Ask one short, friendly question (under 25 words) that tells apart the two or three requests \
they most likely mean, in plain words, e.g. "Is that a return, or hasn't the order arrived \
yet?". Don't ask for order numbers or personal details, and don't promise anything."""


class Clarification(BaseModel):
    question: str = Field(description="The one question to ask the customer.")


def clarify_system(ontology: Ontology) -> str:
    return CLARIFY_INSTRUCTIONS.format(intents="\n".join(f"- {i.name}" for i in ontology.intents))


def clarifying_question(conv: Conversation, system: str, model: str) -> str:
    """A question that tells the likely requests apart, or the fixed one if the call fails."""
    req = llm.Request(model, system, format_conversation(conv), max_tokens=200)
    try:
        return llm.structured(req, Clarification).output.question
    except llm.LLMError:
        return CLARIFYING_QUESTION


OUTCOME_TEXT: dict[Outcome, str] = {
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
    parser.add_argument("--model", default=ROUTER_MODEL, choices=sorted(llm.PRICES))
    parser.add_argument("--show-prompt", action="store_true", help="print the intent prompt")
    args = parser.parse_args()

    ontology = load_ontology()
    prompts = load_router_prompts(ontology)
    clarify = clarify_system(ontology)
    if args.message:
        messages: Iterable[str] = [args.message]
    else:
        print(f"BrownBox router · ontology v{ontology.version} · {args.model}")
        print("You're the customer: one message per line, Enter on an empty line to finish.\n")
        # Shown, not sent: the router judges the customer's words, and leaving the greeting out
        # of the transcript keeps the tested demo answers (and their cache) unchanged.
        print(f"Agent: {GREETING}")
        messages = typed_messages()

    turns: list[Turn] = []
    try:
        for text in messages:
            turns.append(Turn(role="customer", speaker="Customer", text=text))
            conv = Conversation(id=0, split="synthetic", turns=tuple(turns))
            steps = route_conversation(conv, prompts, model=args.model).steps
            decision = decide(ontology, steps)
            print(describe(steps, decision, ontology) + "\n")
            if args.show_prompt:
                print(f"--- system prompt ---\n{prompts.system}\n\n--- conversation ---")
                print(format_conversation(conv, numbered=True) + "\n")
            if decision.outcome == "clarify":
                # Into the transcript, as in a real conversation, so the answer reads in context.
                question = clarifying_question(conv, clarify, args.model)
                print(f"Agent: {question}")
                turns.append(Turn(role="staff", speaker="Agent", text=question))
    except KeyboardInterrupt:
        print()


def typed_messages() -> Iterator[str]:
    """Customer messages typed at the prompt, until an empty line or Ctrl-D."""
    while True:
        try:
            text = input("Customer: ").strip()
        except EOFError:
            print()
            return
        if not text:
            return
        yield text


if __name__ == "__main__":
    main()
