"""Incidente → recomendación → aprobación (vía el formulario HTML real,
no solo la API JSON) → auditoría → handover, encadenados de verdad.
"""
from __future__ import annotations

import re


def test_operator_reviews_and_approves_via_web_ui(approver_client, audit_log):
    queue = approver_client.get("/incidents")
    assert queue.status_code == 200
    assert "incident-smoke-001" in queue.text

    detail = approver_client.get("/incidents/incident-smoke-001")
    assert detail.status_code == 200
    assert "Hechos" in detail.text and "Inferencias" in detail.text

    form = approver_client.get("/incidents/incident-smoke-001/approve")
    assert form.status_code == 200
    action_id = re.search(r'name="action_id" value="([^"]+)"', form.text).group(1)

    # Regresión: el checkbox de confirmación decía "he revisado el target
    # de la acción" pero mostraba recommendation.selected_action (el
    # nombre de la herramienta, "isolate_kubernetes_workload") en vez del
    # target real del PolicyDecision ("deployment/gseg-simulado") — un
    # operador confirmaba haber revisado el target sin que la UI se lo
    # mostrara nunca.
    assert "deployment/gseg-simulado" in form.text
    checkbox_label = re.search(r'for="target-confirmed">(.*?)</label>', form.text, re.DOTALL).group(1)
    assert "isolate_kubernetes_workload" not in checkbox_label

    submit = approver_client.post(
        "/incidents/incident-smoke-001/approve",
        data={
            "decision": "APPROVE",
            "reason": "Revisado el dry-run, sin impacto en otros servicios afectados",
            "target_confirmed": "true",
            "action_id": action_id,
        },
        follow_redirects=False,
    )
    assert submit.status_code == 303
    assert submit.headers["location"] == "/incidents/incident-smoke-001"

    assert len(audit_log.all()) == 1
    entry = audit_log.all()[0]
    assert entry.actor == "soc-1"
    assert entry.action == "approval.create"

    # La Approval quedó accesible vía la API (mismo repositorio subyacente).
    approvals = approver_client.get("/api/incidents").json()  # sanity: la API sigue viva tras el flujo web
    assert approvals


def test_approve_then_export_handover(approver_client):
    action_id = "policy-smoke-001"  # decision_id real, fixtures/smoke/policy-decision/policy-decision-001.json
    approval = approver_client.post(
        "/api/approvals",
        json={
            "action_id": action_id,
            "decision": "APPROVE",
            "reason": "Revisado y confirmado antes de exportar al SOC",
            "target_confirmed": True,
        },
    )
    assert approval.status_code == 201

    export = approver_client.post(
        "/api/handover/incident-smoke-001/export", json={"tlp": "AMBER"}
    )
    assert export.status_code == 201

    history = approver_client.get("/api/handover/incident-smoke-001/history")
    assert len(history.json()) == 1
