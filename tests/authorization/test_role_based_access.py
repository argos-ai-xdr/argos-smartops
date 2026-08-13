from __future__ import annotations

from api.auth import Operator, get_current_operator


def test_wrong_role_cannot_create_approval(app):
    app.dependency_overrides[get_current_operator] = lambda: Operator(subject="x", role="xdr-data")
    from fastapi.testclient import TestClient

    client = TestClient(app)
    r = client.post(
        "/api/approvals",
        json={"action_id": "pol-1", "decision": "APPROVE", "reason": "motivo suficientemente largo", "target_confirmed": True},
    )
    assert r.status_code == 403


def test_soc_approver_role_can_create_approval(app):
    app.dependency_overrides[get_current_operator] = lambda: Operator(subject="soc-1", role="soc-approver")
    from fastapi.testclient import TestClient

    client = TestClient(app)
    r = client.post(
        "/api/approvals",
        json={
            "action_id": "policy-smoke-001",  # decision_id real, fixtures/smoke/policy-decision/policy-decision-001.json
            "decision": "APPROVE",
            "reason": "motivo suficientemente largo",
            "target_confirmed": True,
        },
    )
    assert r.status_code == 201


def test_self_approval_by_the_autonomous_requester_is_rejected(app):
    from fastapi.testclient import TestClient

    from api.approvals import REQUESTER_SYSTEM_ID

    app.dependency_overrides[get_current_operator] = lambda: Operator(subject=REQUESTER_SYSTEM_ID, role="soc-approver")
    client = TestClient(app)
    r = client.post(
        "/api/approvals",
        json={"action_id": "pol-1", "decision": "APPROVE", "reason": "motivo suficientemente largo", "target_confirmed": True},
    )
    assert r.status_code == 403


def test_unauthenticated_request_to_protected_route_does_not_silently_succeed(unauthenticated_client):
    """Sin override de get_current_operator, la app real lanzaría (no hay
    Keycloak todavía) — lo que NUNCA debe pasar es un 2xx sin identidad."""
    r = unauthenticated_client.post(
        "/api/approvals",
        json={"action_id": "pol-1", "decision": "APPROVE", "reason": "motivo suficientemente largo", "target_confirmed": True},
    )
    assert r.status_code >= 400


def test_read_only_incident_routes_do_not_require_a_role(approver_client):
    """La cola de incidentes es de lectura para cualquier operador
    autenticado — no debería exigir el rol soc-approver específicamente
    (eso es solo para aprobar/rechazar)."""
    r = approver_client.get("/api/incidents")
    assert r.status_code == 200
