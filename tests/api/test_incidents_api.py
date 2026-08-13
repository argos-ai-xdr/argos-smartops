from __future__ import annotations


def test_list_incidents_returns_seeded_incident(approver_client):
    r = approver_client.get("/api/incidents")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["incident_id"] == "incident-smoke-001"


def test_get_incident_detail_separates_facts_and_inferences(approver_client):
    r = approver_client.get("/api/incidents/incident-smoke-001")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"incident_id", "severity", "facts", "inferences"}


def test_get_unknown_incident_is_404(approver_client):
    r = approver_client.get("/api/incidents/does-not-exist")
    assert r.status_code == 404
