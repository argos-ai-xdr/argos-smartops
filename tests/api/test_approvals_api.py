from __future__ import annotations


def _payload(**overrides):
    base = {
        "action_id": "pol-smoke-001",
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
