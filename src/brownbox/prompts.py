"""Text the LLM sees: conversations, and the ontology rendered as instructions.

One renderer for every stage (pre-labelling, classifying), so they all read the same ontology.
"""

from collections.abc import Mapping

from brownbox.models import Conversation
from brownbox.ontology import Ontology

EXAMPLE_MESSAGES = 2  # Customer messages shown per few-shot example.


def format_conversation(conv: Conversation, numbered: bool = False) -> str:
    """The transcript, one turn per paragraph. Numbered marks customer messages C1, C2..."""
    lines, n = [], 0
    for turn in conv.turns:
        if turn.role == "customer":
            n += 1
            label = f"Customer (C{n})" if numbered else "Customer"
        else:
            label = turn.speaker
        lines.append(f"{label}: {turn.text}")
    return "\n\n".join(lines)


def render_ontology(ontology: Ontology, examples: Mapping[int, Conversation]) -> str:
    """Every intent and guard as instructions, with the customer's opening words as examples.

    `examples` must hold the DEV conversations the ontology lists as examples.
    """
    lines = ["# Intents", ""]
    for d in ontology.domains:
        lines.append(f"## {d.name}")
        for i in (i for i in ontology.intents if i.domain == d.id):
            lines += ["", f"### {i.id}: {i.name}", i.definition]
            lines.append("Includes: " + "; ".join(i.includes))
            if i.excludes:
                lines.append("Excludes: " + "; ".join(i.excludes))
            lines += [f"Versus {other}: {note}" for other, note in i.boundaries.items()]
            for conv_id in i.examples:
                opening = [t.text for t in examples[conv_id].turns if t.role == "customer"]
                lines.append(f'Example: "{" / ".join(opening[:EXAMPLE_MESSAGES])}"')
        lines.append("")
    lines += [
        "### other",
        "The customer wants something none of the intents above covers.",
        "",
        "# Guards",
        "",
        "A guard is a yes/no check that can fire on any customer message, whatever the intent.",
    ]
    for g in ontology.guards:
        lines += [
            "",
            f"### {g.id}: {g.name}",
            g.definition,
            "Fires on: " + "; ".join(g.fires_on),
            "Does not fire on: " + "; ".join(g.not_on),
        ]
    return "\n".join(lines)
