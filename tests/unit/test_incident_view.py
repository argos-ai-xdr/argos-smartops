from __future__ import annotations

from api.incidents import to_incident_detail, to_queue_item


def _sample_incident():
    return {
        "incident_id": "inc-1",
        "severity": "high",
        "confidence": "medium",
        "member_event_ids": ["evt-1"],
        "timeline": [{"timestamp": "2026-01-01T00:00:00Z", "description": "x"}],
        "evidence_refs": ["ref-1"],
        "entities": [{"type": "asset", "id": "a1"}],
        "attack_techniques": ["T1078"],
        "observed_at": "2026-01-01T00:00:00Z",
    }


def test_facts_and_inferences_are_disjoint_top_level_keys():
    detail = to_incident_detail(_sample_incident())
    assert set(detail.keys()) == {"incident_id", "severity", "facts", "inferences"}
    assert "attack_techniques" not in detail["facts"]
    assert "confidence" not in detail["facts"]
    assert "member_event_ids" not in detail["inferences"]


def test_facts_contains_only_observed_fields():
    detail = to_incident_detail(_sample_incident())
    assert detail["facts"]["member_event_ids"] == ["evt-1"]
    assert detail["facts"]["evidence_refs"] == ["ref-1"]


def test_inferences_contains_only_derived_fields():
    detail = to_incident_detail(_sample_incident())
    assert detail["inferences"]["attack_techniques"] == ["T1078"]
    assert detail["inferences"]["confidence"] == "medium"


def test_missing_attack_techniques_defaults_to_empty_list():
    incident = _sample_incident()
    del incident["attack_techniques"]
    detail = to_incident_detail(incident)
    assert detail["inferences"]["attack_techniques"] == []


def test_queue_item_extracts_affected_assets_from_entities():
    item = to_queue_item(_sample_incident())
    assert item["affected_assets"] == ["a1"]
    assert item["has_evidence"] is True
