"""Ciclo de vida del envío del SOC handover (P0): TLP, ACK, reintento,
historial de exportaciones. No reconstruye la redacción por TLP — eso es
`argos-core/services/soc_adapter`; aquí se gestiona SOLO el estado del
envío (pending → sent → acked, o failed → retry).

Cada transición exige un operador autenticado y queda en AuditLog — un
handover expone contenido con clasificación TLP a un tercero (el SOC), así
que no puede quedar sin atribuir a nadie, igual que una Approval. Encontrado
ejecutando la app sin ningún token: /export devolvía 201 para cualquiera, y
api/audit.py ya documentaba (incorrectamente) que "cada export de handover
queda registrado" sin que ningún endpoint de este módulo llamara a
AuditLog.record.

Sin endpoint SOC real todavía (ARG-022): el envío se simula (siempre
"sent" salvo que el propio caller pida simular un fallo, útil para probar
el ciclo failed→retry sin depender de un servicio externo que no existe).
"""
from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.audit import AuditLog, get_audit_log
from api.auth import Operator, get_current_operator
from api.incidents import get_repositories
from api.repository import Repositories

router = APIRouter(prefix="/handover", tags=["handover"])

VALID_TLP = {"RED", "AMBER", "GREEN", "CLEAR"}


class ExportRequest(BaseModel):
    tlp: str
    simulate_failure: bool = False  # hook de desarrollo/test, ver docstring del módulo


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


@router.post("/{case_id}/export", status_code=201)
def trigger_export(
    case_id: str,
    payload: ExportRequest,
    operator: Operator = Depends(get_current_operator),
    repos: Repositories = Depends(get_repositories),
    audit: AuditLog = Depends(get_audit_log),
) -> dict:
    if payload.tlp not in VALID_TLP:
        raise HTTPException(status_code=400, detail=f"tlp inválido: {payload.tlp!r}, debe ser uno de {sorted(VALID_TLP)}")

    # uuid4, no un contador basado en len(list_where(...)): dos exports del
    # MISMO case_id en la misma ventana de carrera calculan el mismo count y
    # producen el mismo export_id, y el repositorio en memoria (keyed por
    # export_id) descarta uno en silencio — mismo bug ya encontrado y
    # corregido para approval_id en api/approvals.py.
    export_id = f"exp-{case_id}-{uuid.uuid4().hex[:12]}"
    now = _now_iso()
    record = {
        "export_id": export_id,
        "case_id": case_id,
        "tlp": payload.tlp,
        "status": "failed" if payload.simulate_failure else "sent",
        "attempts": 1,
        "created_at": now,
        "last_attempt_at": now,
        "acked_at": None,
    }
    repos.handovers.add(record)
    audit.record(
        actor=operator.subject,
        action="handover.export.create",
        detail={"export_id": export_id, "case_id": case_id, "tlp": payload.tlp, "status": record["status"]},
    )
    return record


@router.post("/exports/{export_id}/ack")
def acknowledge_export(
    export_id: str,
    operator: Operator = Depends(get_current_operator),
    repos: Repositories = Depends(get_repositories),
    audit: AuditLog = Depends(get_audit_log),
) -> dict:
    record = repos.handovers.get(export_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"export {export_id!r} no encontrado")
    if record["status"] != "sent":
        raise HTTPException(status_code=409, detail=f"no se puede confirmar un export en estado '{record['status']}'")
    record["status"] = "acked"
    record["acked_at"] = _now_iso()
    audit.record(
        actor=operator.subject,
        action="handover.export.ack",
        detail={"export_id": export_id, "case_id": record["case_id"]},
    )
    return record


@router.post("/exports/{export_id}/retry")
def retry_export(
    export_id: str,
    operator: Operator = Depends(get_current_operator),
    repos: Repositories = Depends(get_repositories),
    audit: AuditLog = Depends(get_audit_log),
) -> dict:
    record = repos.handovers.get(export_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"export {export_id!r} no encontrado")
    if record["status"] != "failed":
        raise HTTPException(status_code=409, detail=f"solo se puede reintentar un export en estado 'failed', está en '{record['status']}'")
    record["attempts"] += 1
    record["status"] = "sent"
    record["last_attempt_at"] = _now_iso()
    audit.record(
        actor=operator.subject,
        action="handover.export.retry",
        detail={"export_id": export_id, "case_id": record["case_id"], "attempts": record["attempts"]},
    )
    return record


@router.get("/{case_id}/history")
def get_export_history(case_id: str, repos: Repositories = Depends(get_repositories)) -> list[dict]:
    return repos.handovers.list_where(case_id=case_id)
