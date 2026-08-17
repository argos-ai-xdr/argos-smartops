from __future__ import annotations


def _payload(**overrides):
    base = {
        "action_id": "policy-smoke-001",  # decision_id real, fixtures/smoke/policy-decision/policy-decision-001.json
        "decision": "APPROVE",
        "reason": "Dry-run verificado sin impacto en otros servicios",
        "target_confirmed": True,
    }
    base.update(overrides)
    return base


def test_create_approval_succeeds_and_validates_against_real_schema(approver_client):
    r = approver_client.post("/api/approvals", json=_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["approver_id"] == "soc-1"
    assert body["role"] == "soc-approver"


def test_approval_without_target_confirmation_is_rejected(approver_client):
    r = approver_client.post("/api/approvals", json=_payload(target_confirmed=False))
    assert r.status_code == 400


def test_approval_with_short_reason_is_rejected_by_pydantic(approver_client):
    r = approver_client.post("/api/approvals", json=_payload(reason="short"))
    assert r.status_code == 422


def test_approval_with_invalid_decision_is_rejected(approver_client):
    r = approver_client.post("/api/approvals", json=_payload(decision="MAYBE"))
    assert r.status_code == 422


def test_two_approvals_for_same_action_get_different_ids(approver_client):
    r1 = approver_client.post("/api/approvals", json=_payload())
    r2 = approver_client.post("/api/approvals", json=_payload())
    assert r1.json()["approval_id"] != r2.json()["approval_id"]


def test_approval_for_unknown_action_id_is_rejected(approver_client):
    r = approver_client.post("/api/approvals", json=_payload(action_id="no-existe"))
    assert r.status_code == 404


def test_create_approval_is_recorded_in_the_audit_log(approver_client, audit_log):
    """Regresión: POST /approvals (el endpoint real, vía API) nunca
    llamaba a AuditLog.record — solo web/routes.py auditaba
    "approval.create", y solo cuando la aprobación llegaba por el
    formulario web, nunca por la API directamente. La accion mas critica
    de todo el sistema (autorizar execute) quedaba sin rastro de
    auditoria cuando no pasaba por la UI."""
    r = approver_client.post("/api/approvals", json=_payload())
    approval_id = r.json()["approval_id"]

    entries = audit_log.all()
    assert len(entries) == 1
    assert entries[0].action == "approval.create"
    assert entries[0].actor == "soc-1"
    assert entries[0].detail["approval_id"] == approval_id
    assert entries[0].detail["decision"] == "APPROVE"


def test_plan_hash_is_derived_from_the_real_policy_decision_not_action_id_or_decision(approver_client):
    """Regresión del bug real: plan_hash debía depender de
    tool/target/action del PolicyDecision, no de action_id+decision — dos
    Approvals para la MISMA acción con distinta decisión (APPROVE/REJECT)
    deben producir el MISMO plan_hash, porque el plan que se aprueba o
    rechaza es el mismo."""
    approve = approver_client.post("/api/approvals", json=_payload(decision="APPROVE")).json()
    reject = approver_client.post("/api/approvals", json=_payload(decision="REJECT")).json()
    assert approve["signature_ref"] != reject["signature_ref"]  # distinto approval_id
    # pero ambos firman el mismo plan_hash implícito: si se revalida con el
    # mismo current_plan_hash, la única diferencia relevante es la decisión.
    from api.approvals import compute_plan_hash, compute_signature_ref

    decision = {"tool": "isolate_kubernetes_workload", "action": "execute", "target": "deployment/gseg-simulado"}
    plan_hash = compute_plan_hash(**decision)
    assert approve["signature_ref"] == compute_signature_ref(approve["approval_id"], plan_hash)
    assert reject["signature_ref"] == compute_signature_ref(reject["approval_id"], plan_hash)
