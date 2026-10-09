"""Stage 5: hand-label practice conversations against the ontology, one at a time.

    uv run python -m brownbox.label             # the 30 blind labels, in a fixed random order
    uv run python -m brownbox.label --assisted  # 55 of the other 170, with model suggestions

Each label is saved as soon as you confirm it, so you can stop (q) and resume any time.
Blind means no model suggestion is shown: these 30 measure how much suggestions sway you later.
Assisted covers every conversation the two models disagree on (25), plus a random 30 of those
they fully agree on; the audit measures how far to trust the remaining agreed ones unlabelled.
The intent both models gave is pre-selected; where they disagree on it, nothing is shown and
that label counts as blind.
"""

import argparse
import json
import random
import shutil
import time
from collections.abc import Callable, Container
from dataclasses import dataclass
from pathlib import Path

from brownbox.models import Adjudication, Conversation, GoldLabel
from brownbox.ontology import Ontology, load_ontology
from brownbox.parse import load
from brownbox.paths import DATA

GOLD_DIR = DATA / "gold"
PRACTICE_LABELS = GOLD_DIR / "practice.jsonl"
PRELABELS = GOLD_DIR / "prelabels.jsonl"
ADJUDICATED = GOLD_DIR / "adjudicated.jsonl"
SEED = 11
BLIND_BATCH = 30
PRACTICE_SIZE = 200
AUDIT_SIZE = 30  # Hand-labelled sample of the conversations the models fully agree on.
OTHER = "other"
STAFF_PREVIEW = 140  # Staff turns are shortened: the customer's words are what matter.
STEPS = 6

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
SUGGESTED = "\033[1;30;46m"  # Bold black on cyan: the models' suggestion.
CLEAR = "\033[2J\033[H"  # Clear the screen, cursor to the top.


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


def load_adjudicated(path: Path) -> dict[int, GoldLabel]:
    """Corrected labels by conversation id; a later correction replaces an earlier one."""
    if not path.exists():
        return {}
    with path.open() as f:
        corrections = [Adjudication.model_validate_json(line) for line in f if line.strip()]
    return {c.label.id: c.label for c in corrections}


def adjudicate(
    path: Path, original: GoldLabel, changes: dict[str, object], reason: str
) -> GoldLabel:
    """Save a corrected copy of a label (fields in `changes` replaced), validated, with the
    reason for the change."""
    label = GoldLabel.model_validate(original.model_dump() | changes)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(Adjudication(label=label, reason=reason).model_dump_json() + "\n")
    return label


@dataclass(frozen=True)
class Suggestions:
    primary: dict[int, str]  # Conversation id -> the primary intent every model gave.
    agreed: dict[int, GoldLabel]  # Conversation id -> the full label every model gave (silver).


def load_suggestions(path: Path, ontology_version: str) -> Suggestions:
    """What the pre-labelling models agree on, per conversation."""
    primaries: dict[int, set[str]] = {}
    answers: dict[int, set[str]] = {}
    for line in path.read_text().splitlines():
        record = json.loads(line)
        primaries.setdefault(record["id"], set()).add(record["primary"])
        answer = {k: v for k, v in record.items() if k != "model"}
        answers.setdefault(record["id"], set()).add(json.dumps(answer, sort_keys=True))
    silver = {"mode": "silver", "ontology_version": ontology_version}
    return Suggestions(
        primary={i: next(iter(p)) for i, p in primaries.items() if len(p) == 1},
        agreed={
            i: GoldLabel.model_validate(json.loads(next(iter(a))) | silver)
            for i, a in answers.items()
            if len(a) == 1
        },
    )


def assisted_batch(
    candidates: list[Conversation], agreed: Container[int], audit_size: int = AUDIT_SIZE
) -> list[Conversation]:
    """Every conversation the models disagree on, plus the first `audit_size` they fully agree on.

    Candidates are in labelling order (a fixed shuffle), so the audit is a random sample. The
    rest of the agreed ones are not hand-labelled: the audit measures how far to trust them.
    """
    audit = {c.id for c in [c for c in candidates if c.id in agreed][:audit_size]}
    return [c for c in candidates if c.id not in agreed or c.id in audit]


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


def parse_intent(
    text: str, choices: list[str], optional: bool, default: str | None = None
) -> str | None:
    """'0' is other, '1'..'n' an intent. Blank gives the default, or none if optional."""
    text = text.strip()
    if not text and (default or optional):
        return default
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


def parse_guards(text: str, keys: dict[str, str], n_customer: int) -> dict[str, int]:
    """'f3 w5': fraud from customer message 3, wants-human from 5. The number is required."""
    guards = {}
    for item in text.replace(",", " ").split():
        key, number = item[0], item[1:]
        if key not in keys:
            raise ValueError(f"unknown guard {key!r}: use {', '.join(sorted(keys))}")
        if not number.isdigit() or not 1 <= int(number) <= n_customer:
            raise ValueError(f"{item}: message number must be 1 to {n_customer}")
        guards[keys[key]] = int(number)
    return dict(sorted(guards.items()))


def show(conv: Conversation, position: str) -> int:
    """Clear the screen and print the conversation; return how many customer messages it has."""
    print(f"{CLEAR}{BOLD}── {position} · conversation {conv.id} ──{RESET}\n")
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


def menu(ontology: Ontology, suggested: str | None = None) -> list[str]:
    """Print the numbered intents in columns under their domain, the suggested one highlighted.

    Returns the intent ids in number order.
    """
    choices = [i.id for i in ontology.intents]
    width = max(len(i.name) for i in ontology.intents) + 5  # "28 " plus a gap.
    columns = max(1, (shutil.get_terminal_size().columns - 2) // width)
    print(f"{BOLD}Intents{RESET}  {DIM}0 other{RESET}")
    for d in ontology.domains:
        cells = []
        for number, intent in enumerate(ontology.intents, start=1):
            if intent.domain != d.id:
                continue
            cell = f"{number:>2} {intent.name}".ljust(width)
            cells.append(f"{SUGGESTED}{cell}{RESET}" if intent.id == suggested else cell)
        print(f"{DIM}{d.name}{RESET}")
        for start in range(0, len(cells), columns):
            print("  " + "".join(cells[start : start + columns]))
    return choices


def describe(label: GoldLabel, names: dict[str, str]) -> str:
    """The label as a short card, one field per line, for checking before saving."""

    def name(intent: str | None) -> str:
        return names[intent] if intent else "none"

    switch = f"at C{label.switch_at} to {name(label.switch_to)}" if label.switch_at else "none"
    guards = ", ".join(f"{g} from C{m}" for g, m in label.guards.items()) or "none"
    return "\n".join(
        [
            f"  Primary   {name(label.primary)}, clear from C{label.clear_at}",
            f"  Second    {name(label.secondary)}",
            f"  Switch    {switch}",
            f"  Guards    {guards}",
            f"  Note      {label.note or '-'}",
        ]
    )


def step(number: int, title: str, hint: str) -> str:
    """A prompt like '2/6 Second request   both live at once? ...: '."""
    return f"{DIM}{number}/{STEPS}{RESET} {BOLD}{title:<14}{RESET} {DIM}{hint}:{RESET} "


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


def label_one(
    conv: Conversation, ontology: Ontology, position: str, suggested: str | None = None
) -> GoldLabel:
    n = show(conv, position)
    choices = menu(ontology, suggested)
    keys = guard_keys(ontology)
    names = {i.id: i.name for i in ontology.intents} | {OTHER: "other"}

    hint = ""
    if suggested:
        number = 0 if suggested == OTHER else choices.index(suggested) + 1
        print(f"\n{SUGGESTED} Models suggest: {number} {names[suggested]} {RESET}  Enter accepts")
        hint = f" [{number}]"
    print()
    primary = ask(
        step(1, "Primary intent", f"what they want done{hint}"),
        lambda t: parse_intent(t, choices, optional=False, default=suggested),
    )
    assert primary is not None
    secondary = ask(
        step(2, "Second request", "another request added? number, or Enter for none"),
        lambda t: parse_intent(t, choices, optional=True),
    )
    clear_at = ask(
        step(3, "Clear from", "customer message number, or Enter for C1"),
        lambda t: parse_message(t, n, default=1),
    )
    assert clear_at is not None
    switch_at = ask(
        step(4, "Switch", "first request dropped? message number, or Enter for no"),
        lambda t: parse_message(t, n, None),
    )
    switch_to = None
    if switch_at is not None:
        switch_to = ask(
            step(4, "Switch to", "intent number"), lambda t: parse_intent(t, choices, False)
        )
    guard_names = {g.id: g.name for g in ontology.guards}
    legend = " · ".join(f"{k} {guard_names[g]}" for k, g in sorted(keys.items()))
    print(f"{DIM}           {legend}{RESET}")
    guards = ask(
        step(5, "Guards", "letter + message, e.g. w5, or Enter for none"),
        lambda t: parse_guards(t, keys, n),
    )
    note = ask(step(6, "Edge case", "short note, or Enter to skip"), lambda t: t.strip() or None)

    label = GoldLabel(
        id=conv.id,
        primary=primary,
        secondary=secondary,
        clear_at=clear_at,
        switch_at=switch_at,
        switch_to=switch_to,
        guards=guards,
        note=note,
        mode="assisted" if suggested else "blind",
        ontology_version=ontology.version,
    )
    print(f"\n{BOLD}Check:{RESET}\n{describe(label, names)}\n")
    if ask(f"{BOLD}Save?{RESET} Enter saves, r redoes this one: ", str).strip() == "r":
        return label_one(conv, ontology, position, suggested)
    return label


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--assisted", action="store_true", help="55 with model suggestions")
    args = parser.parse_args()

    ontology = load_ontology()
    order = labelling_order(load("practice"))
    done = load_labels(PRACTICE_LABELS)
    suggestions: dict[int, str] = {}
    if args.assisted:
        if any(c.id not in done for c in order[:BLIND_BATCH]):
            raise SystemExit("Finish the 30 blind labels first: run without --assisted.")
        prelabels = load_suggestions(PRELABELS, ontology.version)
        suggestions = prelabels.primary
        batch = assisted_batch(order[BLIND_BATCH:PRACTICE_SIZE], prelabels.agreed)
    else:
        batch = order[:BLIND_BATCH]
    todo = [c for c in batch if c.id not in done]
    print(f"{len(batch) - len(todo)} of {len(batch)} already labelled. q quits; work is saved.")
    start = time.monotonic()
    try:
        for labelled, conv in enumerate(todo):
            position = f"{len(batch) - len(todo) + labelled + 1} of {len(batch)}"
            if labelled:
                each = (time.monotonic() - start) / labelled
                left = each * (len(todo) - labelled)
                position += f" · {each / 60:.1f} min each · about {left / 3600:.1f} h left"
            label = label_one(conv, ontology, position, suggestions.get(conv.id))
            save_label(PRACTICE_LABELS, label)
    except (Quit, EOFError, KeyboardInterrupt):
        print("\nStopped. Run again to carry on where you left off.")
        return
    print(f"\nAll {len(batch)} labelled: {PRACTICE_LABELS.name}")


if __name__ == "__main__":
    main()
