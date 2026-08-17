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
    assert set(body.keys()) == {"incident_id", "severity", "status", "facts", "inferences"}


def test_get_unknown_incident_is_404(approver_client):
    r = approver_client.get("/api/incidents/does-not-exist")
    assert r.status_code == 404


def test_new_incident_defaults_to_open_status(approver_client):
    r = approver_client.get("/api/incidents/incident-smoke-001")
    assert r.json()["status"] == "open"


def test_status_transition_open_to_investigating_is_allowed(approver_client):
    r = approver_client.post("/api/incidents/incident-smoke-001/status", json={"status": "investigating"})
    assert r.status_code == 200
    assert r.json()["status"] == "investigating"

    r2 = approver_client.get("/api/incidents/incident-smoke-001")
    assert r2.json()["status"] == "investigating"


def test_status_also_updates_in_the_queue_view(approver_client):
    approver_client.post("/api/incidents/incident-smoke-001/status", json={"status": "closed"})
    r = approver_client.get("/api/incidents")
    item = next(i for i in r.json() if i["incident_id"] == "incident-smoke-001")
    assert item["status"] == "closed"


def test_status_transition_closed_to_investigating_is_rejected_must_reopen_first(approver_client):
    """Regla deliberada: closed -> investigating directo dejaría ambiguo
    si el incidente sigue cerrado o no — debe pasar por 'open' primero."""
    approver_client.post("/api/incidents/incident-smoke-001/status", json={"status": "closed"})
    r = approver_client.post("/api/incidents/incident-smoke-001/status", json={"status": "investigating"})
    assert r.status_code == 409

    r2 = approver_client.post("/api/incidents/incident-smoke-001/status", json={"status": "open"})
    assert r2.status_code == 200


def test_status_transition_to_the_same_status_is_rejected(approver_client):
    r = approver_client.post("/api/incidents/incident-smoke-001/status", json={"status": "open"})
    assert r.status_code == 409


def test_status_invalid_value_is_rejected(approver_client):
    r = approver_client.post("/api/incidents/incident-smoke-001/status", json={"status": "archived"})
    assert r.status_code == 400


def test_status_update_on_unknown_incident_is_404(approver_client):
    r = approver_client.post("/api/incidents/does-not-exist/status", json={"status": "closed"})
    assert r.status_code == 404


def test_status_update_is_recorded_in_the_audit_log(approver_client, audit_log):
    approver_client.post("/api/incidents/incident-smoke-001/status", json={"status": "investigating"})
    actions = [e.action for e in audit_log.all()]
    assert actions[-1] == "incident.status.update"


def test_status_update_without_authentication_does_not_silently_succeed(unauthenticated_client):
    r = unauthenticated_client.post("/api/incidents/incident-smoke-001/status", json={"status": "closed"})
    assert r.status_code >= 400


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
