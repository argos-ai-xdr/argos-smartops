"""Creación de Approval (P0, HITL): motivo obligatorio (Pydantic,
min_length=10), rol autorizado (`require_role("soc-approver")`),
confirmación explícita del target, y un `plan_hash`/`signature_ref`
calculados con la MISMA fórmula que argos-cyber-tools/policies/approval
espera — para que la Approval que emite SmartOps sea la que ese repositorio
sabe validar, no una incompatible por casualidad.

`plan_hash` se deriva del PolicyDecision real (tool/target/action/params)
que `action_id` referencia, no de action_id+decision: una versión anterior
hasheaba (action_id, decision), que ni siquiera con el mismo action_id real
coincide con lo que argos-cyber-tools recalcula en el momento de ejecutar
(ToolCallRequest.tool/target/action) — toda Approval emitida así era
rechazada siempre con "la acción cambió después de aprobarse", un mensaje
engañoso ya que nada había cambiado: las dos fórmulas nunca coincidieron.
Encontrado ejecutando de verdad el código de ambos repos juntos, no
leyéndolos por separado (cada suite de tests solo comprobaba consistencia
interna contra su propia fórmula).

`argos-cyber-tools` revalida todo esto de forma independiente antes de
ejecutar nada (ADR-011): lo de aquí reduce aprobaciones inválidas por error
humano, no es el control de seguridad final.

Cada Approval creada queda en AuditLog — es la acción más crítica de todo
el sistema (autoriza `execute` sobre un recurso real) y hasta ahora este
endpoint, el real (`POST /approvals`), no llamaba a `AuditLog.record` en
absoluto: solo `web/routes.py` auditaba "approval.create", y solo cuando
la aprobación llegaba por el FORMULARIO web, nunca cuando llegaba por la
API directamente. Mismo patrón de bug ya encontrado y corregido en
`api/handover.py` y `api/incidents.py` — encontrado ejecutando la app y
comprobando qué llamaba de verdad a `audit.record`, no leyendo el código.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from generated_contracts import (
    ApprovalCreate,
    ContractValidationError,
    build_registry,
    resolve_contracts_path,
    validate_payload,
)

from api.audit import AuditLog, get_audit_log
from api.auth import Operator, require_role
from api.incidents import get_repositories
from api.repository import Repositories

router = APIRouter(prefix="/approvals", tags=["approvals"])

# Productor autónomo de Recommendation — nunca puede ser también el
# aprobador (segregación de funciones), aunque hoy no hay un "usuario" real
# detrás de él con el que colisionar en la práctica.
REQUESTER_SYSTEM_ID = "argos-core-recommendation-engine"
APPROVAL_TTL_MINUTES = 15


def compute_plan_hash(*, tool: str, target: str, action: str, params: dict | None = None) -> str:
    """Idéntica a argos-cyber-tools/policies/approval.compute_plan_hash — ver
    el docstring del módulo. Duplicada a propósito (mismo patrón que el
    resto de argos-ai-xdr, p. ej. la validación de schemas): cada repo debe
    poder calcularla sin depender de importar código del otro."""
    canonical = json.dumps(
        {"tool": tool, "target": target, "action": action, "params": params or {}},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_signature_ref(approval_id: str, plan_hash: str) -> str:
    return "sha256:" + hashlib.sha256(f"{approval_id}:{plan_hash}".encode()).hexdigest()


@router.post("", status_code=201)
def create_approval(
    payload: ApprovalCreate,
    operator: Operator = Depends(require_role("soc-approver")),
    repos: Repositories = Depends(get_repositories),
    audit: AuditLog = Depends(get_audit_log),
) -> dict:
    if not payload.target_confirmed:
        raise HTTPException(
            status_code=400,
            detail="target_confirmed debe ser true: el operador debe confirmar el target antes de aprobar",
        )
    if operator.subject == REQUESTER_SYSTEM_ID:
        raise HTTPException(status_code=403, detail="segregación de funciones: approver_id == requester_id")

    policy_decision = repos.policy_decisions.get(payload.action_id)
    if policy_decision is None:
        raise HTTPException(
            status_code=404,
            detail=f"no existe un PolicyDecision con decision_id={payload.action_id!r} — "
            "no se puede calcular un plan_hash verificable para esta Approval",
        )

    # uuid4, no un hash de action_id+timestamp en segundos: dos aprobaciones
    # de la MISMA acción dentro del mismo segundo colisionaban (encontrado
    # por un test que crea dos aprobaciones seguidas), y el repositorio en
    # memoria (keyed por approval_id) habría descartado la primera en
    # silencio.
    approval_id = f"appr-{uuid.uuid4().hex[:30]}"
    plan_hash = compute_plan_hash(
        tool=policy_decision["tool"],
        target=policy_decision["target"],
        action=policy_decision["action"],
        params=policy_decision.get("params"),
    )
    issued_at = datetime.datetime.now(datetime.UTC)
    expires_at = issued_at + datetime.timedelta(minutes=APPROVAL_TTL_MINUTES)

    approval_fields = {
        "approval_id": approval_id,
        "action_id": payload.action_id,
        "approver_id": operator.subject,
        "role": operator.role,
        "decision": payload.decision,
        "reason": payload.reason,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "signature_ref": compute_signature_ref(approval_id, plan_hash),
    }
    envelope = {
        "id": approval_id,
        "schema_version": "1.0.0",
        "observed_at": issued_at.isoformat(),
        "producer": "argos-smartops",
        "classification": "internal",
        "run_id": payload.action_id,
        "payload_hash": "sha256:" + hashlib.sha256(json.dumps(approval_fields, sort_keys=True).encode()).hexdigest(),
    }
    full_payload = {**envelope, **approval_fields}

    contracts_path = resolve_contracts_path()
    registry = build_registry(contracts_path)
    errors = validate_payload(contracts_path, registry, "approval", full_payload)
    if errors:
        raise ContractValidationError("approval", errors)

    repos.approvals.add(full_payload)
    audit.record(
        actor=operator.subject,
        action="approval.create",
        detail={
            "approval_id": approval_id,
            "action_id": payload.action_id,
            "decision": payload.decision,
        },
    )
    return full_payload
