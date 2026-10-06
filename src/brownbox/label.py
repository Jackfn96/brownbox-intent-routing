"""Stage 5: hand-label practice conversations against the ontology, one at a time.

    uv run python -m brownbox.label           # the 30 blind labels, in a fixed random order

Each label is saved as soon as you confirm it, so you can stop (q) and resume any time.
Blind means no model suggestion is shown: these 30 measure how much suggestions sway you later.
"""

import argparse
import random
from collections.abc import Callable
from pathlib import Path

from brownbox.models import Conversation, GoldLabel
from brownbox.ontology import Ontology, load_ontology
from brownbox.parse import load
from brownbox.paths import DATA

GOLD_DIR = DATA / "gold"
PRACTICE_LABELS = GOLD_DIR / "practice.jsonl"
SEED = 11
BLIND_BATCH = 30
OTHER = "other"
STAFF_PREVIEW = 140  # Staff turns are shortened: the customer's words are what matter.

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


class Quit(Exception):
    """The labeller typed q. Everything confirmed so far is already saved."""


def labelling_order(convs: list[Conversation], seed: int = SEED) -> list[Conversation]:
    """A fixed random order, so 'the first 30' means the same conversations every time."""
    ordered = sorted(convs, key=lambda c: c.id)
    random.Random(seed).shuffle(ordered)
    return ordered


def load_labels(path: Path) -> dict[int, GoldLabel]:
    if not path.exists():
        return {}
    with path.open() as f:
        labels = [GoldLabel.model_validate_json(line) for line in f if line.strip()]
    return {label.id: label for label in labels}


def save_label(path: Path, label: GoldLabel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(label.model_dump_json() + "\n")


def guard_keys(ontology: Ontology) -> dict[str, str]:
    """One-letter shortcut per guard: the first letter of its id."""
    keys = {g.id[0]: g.id for g in ontology.guards}
    if len(keys) != len(ontology.guards):
        raise ValueError("two guards share a first letter: give them distinct ids")
    return keys


def parse_intent(text: str, choices: list[str], optional: bool) -> str | None:
    """'0' is other, '1'..'n' an intent; blank means none when the field is optional."""
    text = text.strip()
    if not text and optional:
        return None
    if not text.isdigit() or int(text) > len(choices):
        raise ValueError(f"type a number from 0 to {len(choices)}")
    return OTHER if text == "0" else choices[int(text) - 1]


def parse_message(text: str, n_customer: int, default: int | None) -> int | None:
    """A customer message number between 1 and n_customer; blank gives the default."""
    text = text.strip()
    if not text:
        return default
    if not text.isdigit() or not 1 <= int(text) <= n_customer:
        raise ValueError(f"type a customer message number from 1 to {n_customer}")
    return int(text)


def parse_guards(text: str, keys: dict[str, str]) -> tuple[str, ...]:
    letters = text.replace(",", " ").split()
    unknown = [x for x in letters if x not in keys]
    if unknown:
        raise ValueError(f"unknown guard {unknown}: use {', '.join(sorted(keys))}")
    return tuple(sorted({keys[x] for x in letters}))


def show(conv: Conversation, position: str) -> int:
    """Print the conversation; return how many customer messages it has."""
    print(f"\n{BOLD}── {position} · conversation {conv.id} ──{RESET}\n")
    n = 0
    for turn in conv.turns:
        if turn.role == "customer":
            n += 1
            print(f"{BOLD}C{n}  {turn.text}{RESET}\n")
        else:
            short = (
                turn.text if len(turn.text) <= STAFF_PREVIEW else turn.text[:STAFF_PREVIEW] + "…"
            )
            print(f"{DIM}    {turn.speaker}: {short}{RESET}\n")
    return n


def menu(ontology: Ontology) -> list[str]:
    """Print the numbered intent list grouped by domain; return the ids in number order."""
    choices = [i.id for i in ontology.intents]
    print(f"{DIM}  0 other{RESET}")
    for d in ontology.domains:
        items = [
            f"{choices.index(i.id) + 1:>2} {i.name}" for i in ontology.intents if i.domain == d.id
        ]
        print(f"{DIM}{d.name}: " + " · ".join(items) + RESET)
    return choices


def ask[T](prompt: str, parse: Callable[[str], T]) -> T:
    """Keep asking until the answer parses. 'q' quits at any prompt."""
    while True:
        text = input(prompt)
        if text.strip().lower() == "q":
            raise Quit
        try:
            return parse(text)
        except ValueError as e:
            print(f"  {e}")


def label_one(conv: Conversation, ontology: Ontology, position: str) -> GoldLabel:
    n = show(conv, position)
    choices = menu(ontology)
    keys = guard_keys(ontology)
    names = {i.id: i.name for i in ontology.intents} | {OTHER: "other"}

    primary = ask("Primary intent: ", lambda t: parse_intent(t, choices, optional=False))
    assert primary is not None
    secondary = ask("Second request [none]: ", lambda t: parse_intent(t, choices, optional=True))
    clear_at = ask("Clear at customer message [1]: ", lambda t: parse_message(t, n, default=1))
    assert clear_at is not None
    switch_at = ask("Changes request at message [no]: ", lambda t: parse_message(t, n, None))
    switch_to = None
    if switch_at is not None:
        switch_to = ask("  ...changes to intent: ", lambda t: parse_intent(t, choices, False))
    guards = ask(f"Guards {'/'.join(sorted(keys))} [none]: ", lambda t: parse_guards(t, keys))

    label = GoldLabel(
        id=conv.id,
        primary=primary,
        secondary=secondary,
        clear_at=clear_at,
        switch_at=switch_at,
        switch_to=switch_to,
        guards=guards,
        mode="blind",
        ontology_version=ontology.version,
    )
    summary = f"{names[primary]}, clear at C{clear_at}"
    if secondary:
        summary += f", then {names[secondary]}"
    if switch_to:
        summary += f", switches to {names[switch_to]} at C{switch_at}"
    if guards:
        summary += f", guards: {', '.join(guards)}"
    if ask(f"{BOLD}Save: {summary}?{RESET} [Enter = yes, r = redo] ", str).strip() == "r":
        return label_one(conv, ontology, position)
    return label


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=BLIND_BATCH, help="how many to label")
    args = parser.parse_args()

    ontology = load_ontology()
    batch = labelling_order(load("practice"))[: args.count]
    done = load_labels(PRACTICE_LABELS)
    todo = [c for c in batch if c.id not in done]
    print(f"{len(batch) - len(todo)} of {len(batch)} already labelled. q quits; work is saved.")
    try:
        for k, conv in enumerate(todo, start=len(batch) - len(todo) + 1):
            save_label(PRACTICE_LABELS, label_one(conv, ontology, f"{k} of {len(batch)}"))
    except (Quit, EOFError, KeyboardInterrupt):
        print("\nStopped. Run again to carry on where you left off.")
        return
    print(f"\nAll {len(batch)} labelled: {PRACTICE_LABELS.name}")


if __name__ == "__main__":
    main()
