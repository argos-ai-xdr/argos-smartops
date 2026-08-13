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
