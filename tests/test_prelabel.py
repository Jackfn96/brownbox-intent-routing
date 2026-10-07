from brownbox.ontology import load_ontology
from brownbox.prelabel import proposal_schema, to_proposal

ONTOLOGY = load_ontology()


def test_schema_lists_only_real_ids_as_choices() -> None:
    schema = proposal_schema(ONTOLOGY).model_json_schema()
    primary = schema["properties"]["primary"]["enum"]
    assert set(primary) == {i.id for i in ONTOLOGY.intents} | {"other"}
    assert "none" in schema["properties"]["secondary"]["enum"]


def test_to_proposal_maps_none_and_zero_to_null() -> None:
    p = to_proposal(
        {
            "primary": "initiate_return",
            "secondary": "none",
            "clear_at": 1,
            "switch_at": 0,
            "switch_to": "none",
            "guards": [{"guard": "fraud_or_takeover", "message": 2}],
        }
    )
    assert (p.secondary, p.switch_at, p.switch_to) == (None, None, None)
    assert p.guards == {"fraud_or_takeover": 2}
