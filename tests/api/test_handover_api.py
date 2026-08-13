from __future__ import annotations


def test_export_ack_and_history_cycle(approver_client):
    r1 = approver_client.post("/api/handover/case-x/export", json={"tlp": "AMBER"})
    assert r1.status_code == 201
    export_id = r1.json()["export_id"]
    assert r1.json()["status"] == "sent"

    r2 = approver_client.post(f"/api/handover/exports/{export_id}/ack")
    assert r2.status_code == 200
    assert r2.json()["status"] == "acked"
    assert r2.json()["acked_at"] is not None

    r3 = approver_client.get("/api/handover/case-x/history")
    assert len(r3.json()) == 1


def test_invalid_tlp_is_rejected(approver_client):
    r = approver_client.post("/api/handover/case-y/export", json={"tlp": "PURPLE"})
    assert r.status_code == 400


def test_failed_export_can_be_retried_and_not_acked_directly(approver_client):
    r1 = approver_client.post("/api/handover/case-z/export", json={"tlp": "RED", "simulate_failure": True})
    export_id = r1.json()["export_id"]
    assert r1.json()["status"] == "failed"

    r2 = approver_client.post(f"/api/handover/exports/{export_id}/ack")
    assert r2.status_code == 409  # no se puede confirmar algo que nunca se envió

    r3 = approver_client.post(f"/api/handover/exports/{export_id}/retry")
    assert r3.status_code == 200
    assert r3.json()["status"] == "sent"
    assert r3.json()["attempts"] == 2


def test_retry_of_already_sent_export_is_rejected(approver_client):
    r1 = approver_client.post("/api/handover/case-w/export", json={"tlp": "GREEN"})
    export_id = r1.json()["export_id"]
    r2 = approver_client.post(f"/api/handover/exports/{export_id}/retry")
    assert r2.status_code == 409


def test_unknown_export_operations_are_404(approver_client):
    assert approver_client.post("/api/handover/exports/nope/ack").status_code == 404
    assert approver_client.post("/api/handover/exports/nope/retry").status_code == 404


def test_two_exports_for_same_case_get_different_ids_even_under_a_stale_count(approver_client, app):
    """Regresión: export_id se generaba como
    f"exp-{case_id}-{len(list_where(...)) + 1}". Dos llamadas SECUENCIALES ya
    daban ids distintos (el count avanza), así que eso no demuestra nada —
    el bug real es bajo carrera: dos requests que leen el count ANTES de que
    ninguna de las dos haya escrito ven el mismo len(...) y calculan el
    mismo export_id, y el repositorio en memoria (keyed por export_id)
    descarta una en silencio. Se simula esa carrera vaciando el repositorio
    entre ambas llamadas, para que la segunda vea el mismo estado (len=0)
    que vio la primera."""
    r1 = approver_client.post("/api/handover/case-collision/export", json={"tlp": "AMBER"})
    app.state.repositories.handovers._items.clear()  # simula la carrera: la 2ª ve el mismo estado que la 1ª
    r2 = approver_client.post("/api/handover/case-collision/export", json={"tlp": "AMBER"})
    assert r1.json()["export_id"] != r2.json()["export_id"]


def test_export_without_authentication_does_not_silently_succeed(unauthenticated_client):
    """Regresión: /export no exigía ningún operador — cualquiera, sin
    token, podía disparar un handover con contenido clasificado TLP hacia
    el SOC. Mismo principio ya probado para /api/approvals."""
    r = unauthenticated_client.post("/api/handover/case-x/export", json={"tlp": "AMBER"})
    assert r.status_code >= 400


def test_export_ack_and_retry_are_recorded_in_the_audit_log(approver_client, audit_log):
    """Regresión: ningún endpoint de handover llamaba a AuditLog.record,
    aunque api/audit.py ya documentaba (antes en web/audit.py) que 'cada
    export de handover queda registrado'."""
    r1 = approver_client.post("/api/handover/case-audit/export", json={"tlp": "RED", "simulate_failure": True})
    export_id = r1.json()["export_id"]
    approver_client.post(f"/api/handover/exports/{export_id}/retry")

    actions = [e.action for e in audit_log.all()]
    assert actions == ["handover.export.create", "handover.export.retry"]
    assert all(e.actor == "soc-1" for e in audit_log.all())
