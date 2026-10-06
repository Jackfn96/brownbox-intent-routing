from pathlib import Path

import pytest
from pydantic import ValidationError

from brownbox import parse
from brownbox.models import Conversation, Turn

TRANSCRIPT = """Agent: Thank you for calling BrownBox. How can I help?

Customer: Hi, I have a question about my order.

Agent: Sure, what's the order number?

Customer: BB123. It hasn't arrived.
It was due on Monday.

Supervisor: I've taken over this call. Let me check.

Customer: Thanks."""


def test_parse_turns_roles_and_text() -> None:
    turns = parse.parse_turns(TRANSCRIPT)
    assert [t.role for t in turns] == ["staff", "customer"] * 3
    assert turns[4].speaker == "Supervisor"
    assert turns[3].text == "BB123. It hasn't arrived.\nIt was due on Monday."


def test_truncated_transcript_has_no_customer_turn() -> None:
    turns = parse.parse_turns("Agent: You're welcome, Jane. Have a great day!")
    assert not any(t.role == "customer" for t in turns)


def test_cut_after_customer_message() -> None:
    turns = parse.parse_turns(TRANSCRIPT)
    first = parse.cut_after_customer_message(turns, 1)
    assert len(first) == 2
    assert first[-1].text.startswith("Hi, I have a question")
    assert len(parse.cut_after_customer_message(turns, 2)) == 4
    assert parse.cut_after_customer_message(turns, 9) == turns


def test_make_split_sizes_disjoint_and_repeatable() -> None:
    ids = list(range(997))
    split = parse.make_split(ids)
    assert set(split) == set(ids)
    sizes = {s: sum(v == s for v in split.values()) for s in ("locked", "practice", "dev")}
    assert sizes == {"locked": 100, "practice": 200, "dev": 697}
    assert parse.make_split(list(reversed(ids))) == split


def test_load_filters_by_split_and_guards_locked(tmp_path: Path) -> None:
    turns = tuple(parse.parse_turns(TRANSCRIPT))
    path = tmp_path / "parsed.jsonl"
    path.write_text(
        "".join(
            Conversation(id=i, split=s, turns=turns).model_dump_json() + "\n"
            for i, s in [(1, "dev"), (2, "practice"), (3, "locked")]
        )
    )
    assert [c.id for c in parse.load("dev", path=path)] == [1]
    assert [c.id for c in parse.load("locked", unlock=True, path=path)] == [3]
    with pytest.raises(PermissionError):
        parse.load("locked", path=path)


def test_turn_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        Turn(role="bot", speaker="Agent", text="hi")
