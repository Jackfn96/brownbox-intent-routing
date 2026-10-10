"""Run the router's main flows, one short conversation each.

    make demo           # every flow
    make demo FLOW=3    # one flow

Each customer message is routed in turn, as in production, so the output shows what the system
decides after every message.
"""

import argparse

from brownbox.classify import decide, route_conversation, router_prompts
from brownbox.models import Conversation, Turn
from brownbox.ontology import load_ontology
from brownbox.parse import load
from brownbox.route import describe

FLOWS: list[tuple[str, list[str]]] = [
    (
        "Vague start, a return, a follow-up, then fraud mid-conversation",
        [
            "I need some help with my order",
            "I want to return my kettle, it stopped working after two days",
            "Do I need to send it back in the original box?",
            "Actually, can you send the refund to my brother's bank account instead?",
        ],
    ),
    (
        "A real change of request, to a different agent",
        [
            "I want to return my kettle, it stopped working after two days",
            "Do I need to send it back in the original box?",
            "Actually, forget the return. Just cancel my other order for the toaster instead.",
        ],
    ),
    (
        "Can't log in, doesn't know why: the procedure checks the account",
        ["I can't log in and I don't know why"],
    ),
    (
        "Asks for a person mid-conversation",
        [
            "My refund still hasn't arrived and it's been three weeks",
            "I'd like to speak to someone who can help me with this",
        ],
    ),
    (
        "Angry, but still asking for the refund: not a complaint",
        ["This is unacceptable. I demand a full refund for this broken kettle"],
    ),
    (
        "A real complaint",
        ["I want to make a formal complaint. Your courier was rude to me."],
    ),
    (
        "Another language",
        ["Hola, mi pedido no ha llegado todavía. ¿Pueden ayudarme?"],
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--flow", type=int, choices=range(1, len(FLOWS) + 1), help="one flow")
    args = parser.parse_args()

    ontology = load_ontology()
    prompts = router_prompts(ontology, {c.id: c for c in load("dev")})
    for number, (title, messages) in enumerate(FLOWS, start=1):
        if args.flow and number != args.flow:
            continue
        print(f"\n{number}. {title}\n")
        turns = tuple(Turn(role="customer", speaker="Customer", text=m) for m in messages)
        steps = route_conversation(
            Conversation(id=0, split="synthetic", turns=turns), prompts
        ).steps
        for k, message in enumerate(messages, start=1):
            print(f'customer: "{message}"')
            print(describe(steps[:k], decide(ontology, steps[:k]), ontology) + "\n")


if __name__ == "__main__":
    main()
