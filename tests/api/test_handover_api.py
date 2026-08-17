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


def test_close_case_requires_the_most_recent_export_to_be_acked(approver_client):
    r1 = approver_client.post("/api/handover/case-close/export", json={"tlp": "GREEN"})
    export_id = r1.json()["export_id"]

    r_early = approver_client.post("/api/handover/case-close/close")
    assert r_early.status_code == 409  # todavía 'sent', no 'acked'

    approver_client.post(f"/api/handover/exports/{export_id}/ack")
    r_close = approver_client.post("/api/handover/case-close/close")
    assert r_close.status_code == 200
    assert r_close.json()["last_export_id"] == export_id
    assert r_close.json()["closed_by"] == "soc-1"


def test_close_case_cannot_be_closed_twice(approver_client):
    r1 = approver_client.post("/api/handover/case-double-close/export", json={"tlp": "GREEN"})
    export_id = r1.json()["export_id"]
    approver_client.post(f"/api/handover/exports/{export_id}/ack")
    approver_client.post("/api/handover/case-double-close/close")

    r2 = approver_client.post("/api/handover/case-double-close/close")
    assert r2.status_code == 409


def test_close_case_with_no_exports_is_404(approver_client):
    r = approver_client.post("/api/handover/case-never-exported/close")
    assert r.status_code == 404


def test_close_case_uses_the_most_recent_export_not_an_arbitrary_one(approver_client):
    """Regresión conceptual: si un caso tiene dos exports (p. ej. uno
    viejo ya acked y uno nuevo reenviado tras un cambio), cerrar debe
    exigir que el MÁS RECIENTE esté acked — un export viejo acked no
    debe permitir cerrar mientras el más reciente sigue sin confirmar."""
    r1 = approver_client.post("/api/handover/case-two-exports/export", json={"tlp": "GREEN"})
    export_id_1 = r1.json()["export_id"]
    approver_client.post(f"/api/handover/exports/{export_id_1}/ack")

    r2 = approver_client.post("/api/handover/case-two-exports/export", json={"tlp": "GREEN"})
    # el segundo export está 'sent', no 'acked' todavía

    r_close = approver_client.post("/api/handover/case-two-exports/close")
    assert r_close.status_code == 409
    assert r2.json()["export_id"] in r_close.json()["detail"]


def test_close_case_is_recorded_in_the_audit_log(approver_client, audit_log):
    r1 = approver_client.post("/api/handover/case-audit-close/export", json={"tlp": "GREEN"})
    export_id = r1.json()["export_id"]
    approver_client.post(f"/api/handover/exports/{export_id}/ack")
    approver_client.post("/api/handover/case-audit-close/close")

    actions = [e.action for e in audit_log.all()]
    assert actions[-1] == "handover.case.close"


def test_get_case_closure_returns_404_before_closing_and_the_record_after(approver_client):
    r1 = approver_client.post("/api/handover/case-closure-lookup/export", json={"tlp": "GREEN"})
    export_id = r1.json()["export_id"]

    assert approver_client.get("/api/handover/case-closure-lookup/closure").status_code == 404

    approver_client.post(f"/api/handover/exports/{export_id}/ack")
    approver_client.post("/api/handover/case-closure-lookup/close")

    r = approver_client.get("/api/handover/case-closure-lookup/closure")
    assert r.status_code == 200
    assert r.json()["case_id"] == "case-closure-lookup"


def test_close_case_without_authentication_does_not_silently_succeed(unauthenticated_client):
    r = unauthenticated_client.post("/api/handover/some-case/close")
    assert r.status_code >= 400


def test_export_declares_soc_mode_explicitly(approver_client):
    """Propuesta v0.6.25.4 (14.16): 'Modo: SOC_REAL solo con
    endpoint/acuerdo/prueba autorizada; en otro caso SOC_EMULADO con
    contrato idéntico.' Sin él, status='sent' no distingue una entrega
    real de una simulación — algo que un evidence pack no puede dejar
    implícito. Sin cliente SOC real todavía (ARG-022), siempre debe ser
    SOC_EMULATED, nunca SOC_REAL."""
    r = approver_client.post("/api/handover/case-mode/export", json={"tlp": "GREEN"})
    assert r.json()["soc_mode"] == "SOC_EMULATED"

    history = approver_client.get("/api/handover/case-mode/history").json()
    assert history[0]["soc_mode"] == "SOC_EMULATED"
