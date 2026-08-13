"""Prueba real de interoperabilidad con argos-cyber-tools: una Approval
emitida por api.approvals debe ser aceptada por
policies.approval.ApprovalStore.validate_and_consume (argos-cyber-tools) —
el consumidor real de este contrato (ADR-011).

Se saltan si argos-cyber-tools no está clonado como hermano (mismo patrón
que `contracts_path` en tests/conftest.py): no se puede importar código de
un repo que no existe en el entorno actual, pero cuando sí existe, esta
prueba habría detectado el bug real donde api.approvals.compute_plan_hash
hasheaba (action_id, decision) en vez de (tool, target, action, params) —
formato distinto al que argos-cyber-tools recalcula, así que TODA Approval
emitida por SmartOps era rechazada, siempre, con un mensaje engañoso ("la
acción cambió después de aprobarse") que no tenía nada que ver con la causa
real.
"""
from __future__ import annotations

import datetime
import importlib
import pathlib
import sys

import pytest

from api.approvals import compute_plan_hash, compute_signature_ref


def _cyber_tools_path() -> pathlib.Path | None:
    candidate = pathlib.Path(__file__).resolve().parents[3] / "argos-cyber-tools"
    return candidate if candidate.is_dir() else None


@pytest.fixture
def cyber_tools_approval_store():
    cyber_tools_path = _cyber_tools_path()
    if cyber_tools_path is None:
        pytest.skip("argos-cyber-tools no está clonado como hermano de argos-smartops")

    sys.path.insert(0, str(cyber_tools_path))
    try:
        module = importlib.import_module("policies.approval")
    finally:
        sys.path.remove(str(cyber_tools_path))
    return module


def test_approval_issued_by_smartops_is_accepted_by_cyber_tools(cyber_tools_approval_store):
    tool, target, action = "isolate_kubernetes_workload", "deployment/gseg-simulado", "execute"

    # Lo que api.approvals.create_approval calcula, a partir del
    # PolicyDecision real referenciado por action_id.
    plan_hash = compute_plan_hash(tool=tool, target=target, action=action)
    approval_id = "appr-interop-test-0000000000001"
    approval = {
        "approval_id": approval_id,
        "action_id": "policy-smoke-001",
        "approver_id": "soc-1",
        "decision": "APPROVE",
        "expires_at": (
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
        ).isoformat(),
        "signature_ref": compute_signature_ref(approval_id, plan_hash),
    }

    # Lo que argos-cyber-tools recalcula en el momento de ejecutar, a partir
    # del ToolCallRequest real (mismo tool/target/action).
    current_plan_hash = cyber_tools_approval_store.compute_plan_hash(tool=tool, target=target, action=action)

    store = cyber_tools_approval_store.ApprovalStore()
    store.validate_and_consume(
        approval,
        current_plan_hash=current_plan_hash,
        requester_id="argos-core-recommendation-engine",
        executor_id="mcp_gateway",
        now=datetime.datetime.now(datetime.UTC),
    )  # no debe lanzar ApprovalRejected
