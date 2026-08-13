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


def test_incidents_queue_is_ordered_by_severity_descending(approver_client, app):
    """Regresión: web/templates/incidents_queue.html anuncia "ordenados por
    severidad" en su <caption>, pero list_incidents devolvía orden de
    inserción — un incidente low insertado antes que uno critical aparecía
    primero en la cola."""
    for incident_id, severity in [("i-low", "low"), ("i-critical", "critical"), ("i-medium", "medium")]:
        app.state.repositories.incidents.add(
            {
                "incident_id": incident_id,
                "severity": severity,
                "entities": [],
                "observed_at": "2026-08-13T00:00:00Z",
                "evidence_refs": [],
            }
        )

    r = approver_client.get("/api/incidents")
    severities = [item["severity"] for item in r.json()]
    assert severities.index("critical") < severities.index("medium") < severities.index("low")
