"""Parse BrownBox transcripts into turns and make the fixed DEV / practice / locked split."""

import random
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from brownbox.models import Conversation, Split, Turn
from brownbox.paths import DATA, ROOT

RAW = DATA / "conversations.parquet"
PARSED = DATA / "parsed.jsonl"
LOCKED_IDS = DATA / "locked_ids.txt"

SEED = 42
N_LOCKED = 100
N_PRACTICE = 200

# A speaker label at the start of a line, e.g. "Customer:", "Agent:", "Senior Agent John:".
SPEAKER = re.compile(r"^\s*([A-Za-z][A-Za-z ]{0,30}?)\s*:\s*", re.M)


def parse_turns(text: str) -> list[Turn]:
    """Split a transcript into turns. "Customer" is the customer; every other label is staff."""
    matches = list(SPEAKER.finditer(text))
    turns = []
    for m, nxt in zip(matches, [*matches[1:], None], strict=True):
        speaker = m.group(1).strip()
        body = text[m.end() : nxt.start() if nxt else len(text)].strip()
        turns.append(
            Turn(role="customer" if speaker == "Customer" else "staff", speaker=speaker, text=body)
        )
    return turns


def cut_after_customer_message(turns: Sequence[Turn], n: int) -> list[Turn]:
    """The conversation as the router sees it right after the customer's n-th message.

    Returns every turn if the customer sent fewer than n messages.
    """
    seen = 0
    for i, turn in enumerate(turns):
        if turn.role == "customer":
            seen += 1
            if seen == n:
                return list(turns[: i + 1])
    return list(turns)


def make_split(ids: Sequence[int], seed: int = SEED) -> dict[int, Split]:
    """Assign each id to a split. The same ids and seed always give the same split."""
    shuffled = sorted(ids)
    random.Random(seed).shuffle(shuffled)
    split: dict[int, Split] = {i: "locked" for i in shuffled[:N_LOCKED]}
    split |= {i: "practice" for i in shuffled[N_LOCKED : N_LOCKED + N_PRACTICE]}
    split |= {i: "dev" for i in shuffled[N_LOCKED + N_PRACTICE :]}
    return split


def load(split: Split, unlock: bool = False, path: Path = PARSED) -> list[Conversation]:
    """Load parsed conversations for one split.

    The locked set needs unlock=True: it's opened once, for the final score.
    """
    if split == "locked" and not unlock:
        raise PermissionError("The locked set is only for the final score: pass unlock=True.")
    with path.open() as f:
        conversations = [Conversation.model_validate_json(line) for line in f]
    return [c for c in conversations if c.split == split]


def read_transcripts(path: Path = RAW) -> dict[int, str]:
    """Every transcript by id. Only these two columns are ever read."""
    df = pd.read_parquet(path, columns=["id", "conversation"])
    return {int(i): text for i, text in zip(df["id"], df["conversation"], strict=True)}


def split_transcripts(
    transcripts: Mapping[int, str],
) -> tuple[dict[int, list[Turn]], dict[int, Split]]:
    """Parse every transcript, drop any with no customer turn, and split the rest."""
    parsed = {i: parse_turns(text) for i, text in transcripts.items()}
    usable = {i: turns for i, turns in parsed.items() if any(t.role == "customer" for t in turns)}
    return usable, make_split(list(usable))


def main() -> None:
    transcripts = read_transcripts()
    usable, split = split_transcripts(transcripts)
    dropped = sorted(transcripts.keys() - usable.keys())
    with PARSED.open("w") as f:
        for i, turns in usable.items():
            f.write(Conversation(id=i, split=split[i], turns=tuple(turns)).model_dump_json() + "\n")
    locked = sorted(i for i, s in split.items() if s == "locked")
    LOCKED_IDS.write_text("\n".join(map(str, locked)) + "\n")

    print(f"parsed {len(transcripts)}, dropped {len(dropped)} with no customer turn: {dropped}")
    print(f"usable {len(usable)}: {dict(Counter(split.values()))}")
    print(f"wrote {PARSED.relative_to(ROOT)} and {LOCKED_IDS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
