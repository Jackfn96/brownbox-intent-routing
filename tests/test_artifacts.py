"""Checks on the committed data, labels, ontology and results.

These are the claims a reviewer would otherwise have to take on trust: the split is reproducible,
nothing held out leaked into building the ontology, and every saved file is still valid.
"""

import json
from collections import Counter

import pytest

from brownbox import parse
from brownbox.cases import load_cases
from brownbox.discover import OUT as DISCOVERY
from brownbox.evaluate import EVAL_DIR, Report
from brownbox.label import (
    ADJUDICATED,
    LOCKED_LABELS,
    PRACTICE_LABELS,
    PRELABELS,
    load_adjudicated,
    load_labels,
    read_prelabels,
)
from brownbox.models import GoldLabel, Split
from brownbox.ontology import (
    OTHER,
    READABLE,
    UNCLEAR,
    load_ontology,
    non_dev_examples,
    render_markdown,
)

ONTOLOGY = load_ontology()


@pytest.fixture(scope="module")
def split() -> dict[int, Split]:
    _, split = parse.split_transcripts(parse.read_transcripts())
    return split


def ids_in(split: dict[int, Split], name: Split) -> set[int]:
    return {i for i, s in split.items() if s == name}


def test_split_is_reproducible_from_the_raw_data(split: dict[int, Split]) -> None:
    committed = {int(i) for i in parse.LOCKED_IDS.read_text().split()}
    assert ids_in(split, "locked") == committed
    assert Counter(split.values()) == {"dev": 697, "practice": 200, "locked": 100}


def test_labels_come_from_the_split_they_claim(split: dict[int, Split]) -> None:
    practice, locked = ids_in(split, "practice"), ids_in(split, "locked")
    assert set(load_labels(PRACTICE_LABELS)) <= practice
    assert set(load_adjudicated(ADJUDICATED)) <= practice
    assert {p.id for p in read_prelabels(PRELABELS)} <= practice
    assert set(load_labels(LOCKED_LABELS)) <= locked


def test_the_ontology_was_built_only_from_dev(split: dict[int, Split]) -> None:
    dev = ids_in(split, "dev")
    lines = (DISCOVERY / "goals.jsonl").read_text().splitlines()
    assert {json.loads(line)["id"] for line in lines} == dev
    assert non_dev_examples(ONTOLOGY, dev) == []


def test_locked_labels_are_blind_and_on_the_frozen_ontology() -> None:
    labels = load_labels(LOCKED_LABELS).values()
    assert len(labels) == 56
    assert {label.mode for label in labels} == {"blind"}
    assert {label.ontology_version for label in labels} == {"2"}


def test_every_label_uses_intents_and_guards_that_exist() -> None:
    intents = {i.id for i in ONTOLOGY.intents} | {OTHER, UNCLEAR}
    guards = {g.id for g in ONTOLOGY.guards}
    labels: list[GoldLabel] = [
        *load_labels(PRACTICE_LABELS).values(),
        *load_adjudicated(ADJUDICATED).values(),
        *load_labels(LOCKED_LABELS).values(),
    ]
    for label in labels:
        assert {label.primary, label.secondary, label.switch_to} - {None} <= intents, label.id
        assert set(label.guards) <= guards, label.id
    for pre in read_prelabels(PRELABELS):
        assert pre.primary in intents, pre.id


def test_readable_ontology_matches_the_yaml() -> None:
    assert READABLE.read_text() == render_markdown(ONTOLOGY), "run `make ontology`"


def test_hand_written_cases_are_valid() -> None:
    assert len(load_cases(ONTOLOGY)) == 44


def test_saved_reports_still_load() -> None:
    paths = sorted(EVAL_DIR.glob("*.json"))
    assert paths
    for path in paths:
        Report.model_validate_json(path.read_text())
