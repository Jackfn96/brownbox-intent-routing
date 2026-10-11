"""Two models suggest labels for the 170 assisted practice conversations.

Where the two models agree, the labelling tool shows their suggestion for you to confirm.
Where they disagree, you label from scratch. The first 30 (your blind batch) are only
pre-labelled once you've finished them, to measure how much suggestions sway you.

The labellers read whole conversations and are deliberately different models from the
router we evaluate (Haiku, message by message), to limit circularity.
"""

import argparse

from pydantic import BaseModel, Field, create_model

from brownbox import llm
from brownbox.label import (
    BLIND_BATCH,
    PRACTICE_LABELS,
    PRELABELS,
    labelling_order,
    load_labels,
    read_prelabels,
)
from brownbox.models import Conversation, PreLabel, Proposal
from brownbox.ontology import OTHER, Ontology, load_ontology
from brownbox.parse import load
from brownbox.prompts import format_conversation, render_ontology

MODELS = (llm.SONNET, llm.OPUS)
NONE = "none"  # The schema uses "none" / 0 rather than null so every field has fixed choices.

INSTRUCTIONS = """You label customer support conversations from BrownBox, an online retailer, \
against the intent ontology below. Read the whole conversation, then give:

- primary: the first thing the customer wants done, as an intent id, or "other".
- secondary: a second, separate request they add, or null. A follow-up question about the same \
request is not a second request.
- clear_at: the customer message number (C1, C2...) where the primary intent first becomes \
clear. A vague opener like "I have a question about my order" is not clear yet.
- switch_at and switch_to: if the customer abandons their first request for a different one, \
the message number where they do and the new intent; otherwise both null.
- guards: each guard that fires, with the customer message where it first applies. Usually none.

When a guard fires, still give the closest intent as primary."""


class GuardHit(BaseModel):
    guard: str
    message: int


# The shape of a model's answer. proposal_schema narrows it to the ontology's ids; the API's
# fixed-choice fields use "none" and 0 where a Proposal has None.
class Answer(BaseModel):
    primary: str
    secondary: str
    clear_at: int
    switch_at: int
    switch_to: str
    guards: list[GuardHit]


def proposal_schema(ontology: Ontology) -> type[Answer]:
    """The output format sent to the API. Ids are listed as allowed values, so the model can
    only answer with real intents and guards."""
    intents = [*(i.id for i in ontology.intents), OTHER]
    one_of = llm.one_of
    hit = create_model(
        "GuardHitOut",
        __base__=GuardHit,
        guard=(str, one_of([g.id for g in ontology.guards])),
        message=(int, Field(description="Customer message number where it first applies")),
    )
    return create_model(
        "LabelProposal",
        __base__=Answer,
        primary=(str, one_of(intents)),
        secondary=(str, one_of([*intents, NONE], "A second, separate request, or none")),
        clear_at=(int, Field(description="Customer message where the primary becomes clear")),
        switch_at=(int, Field(description="Message where they switch request, or 0 if never")),
        switch_to=(str, one_of([*intents, NONE], "The intent they switch to, or none")),
        guards=(list[hit], Field(description="Guards that fire; usually empty")),
    )


def to_proposal(answer: Answer) -> Proposal:
    """Turn the API's fixed-choice answer back into a Proposal ("none" and 0 become None)."""
    return Proposal(
        primary=answer.primary,
        secondary=None if answer.secondary == NONE else answer.secondary,
        clear_at=answer.clear_at,
        switch_at=answer.switch_at or None,
        switch_to=None if answer.switch_to == NONE else answer.switch_to,
        guards={h.guard: h.message for h in answer.guards},
    )


def suggest(conv: Conversation, model: str, system: str, schema: type[Answer]) -> Proposal:
    req = llm.Request(
        model=model,
        system=system,
        user=format_conversation(conv, numbered=True),
        max_tokens=4000,
        effort="low",
    )
    return to_proposal(llm.structured(req, schema).output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--blind-check",
        action="store_true",
        help="pre-label the 30 blind conversations (only once you've labelled them)",
    )
    args = parser.parse_args()

    ontology = load_ontology()
    order = labelling_order(load("practice"))
    if args.blind_check:
        batch = order[:BLIND_BATCH]
        missing = {c.id for c in batch} - set(load_labels(PRACTICE_LABELS))
        if missing:
            raise SystemExit(f"label the blind batch first: {len(missing)} still to do")
    else:
        batch = order[BLIND_BATCH:]

    examples = {c.id: c for c in load("dev")}
    system = INSTRUCTIONS + "\n\n" + render_ontology(ontology, examples)
    schema = proposal_schema(ontology)
    # Skip what's already saved, before calling the model: a re-run costs nothing.
    done = {(r.id, r.model) for r in read_prelabels(PRELABELS)}
    jobs = [(conv, model) for conv in batch for model in MODELS if (conv.id, model) not in done]
    print(f"pre-labelling {len(jobs)} (conversation, model) pairs not yet saved...", flush=True)
    proposals = llm.run_all(lambda job: suggest(job[0], job[1], system, schema), jobs, "labels")

    PRELABELS.parent.mkdir(parents=True, exist_ok=True)
    with PRELABELS.open("a") as f:
        for (conv, model), p in zip(jobs, proposals, strict=True):
            row = {"id": conv.id, "model": model, "ontology_version": ontology.version}
            f.write(PreLabel.model_validate(p.model_dump() | row).model_dump_json() + "\n")

    in_batch = {c.id for c in batch}
    primaries: dict[int, set[str]] = {}
    for r in read_prelabels(PRELABELS):
        if r.id in in_batch:
            primaries.setdefault(r.id, set()).add(r.primary)
    agree = sum(len(p) == 1 for p in primaries.values())
    print(f"models agree on the primary intent for {agree} of {len(primaries)} conversations")


if __name__ == "__main__":
    main()
