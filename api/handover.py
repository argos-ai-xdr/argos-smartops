"""Ciclo de vida del envío del SOC handover (P0): TLP, ACK, reintento,
historial de exportaciones, cierre del caso. No reconstruye la redacción
por TLP — eso es `argos-core/services/soc_adapter`; aquí se gestiona SOLO
el estado del envío (pending → sent → acked, o failed → retry) y el
cierre del caso una vez que el SOC confirmó recepción.

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

Propuesta v0.6.25.4 (14.16, Slice P0 y límites de ARG-022): "Modo:
SOC_REAL solo con endpoint/acuerdo/prueba autorizada; en otro caso
SOC_EMULATED con contrato idéntico." Cada registro de export lleva
soc_mode explícito — sin él, un status="sent" no distingue una entrega
real de una simulación, algo que un evidence pack no puede dejar
implícito. Hoy siempre es SOC_EMULATED porque, como dice el párrafo
anterior, no existe ningún endpoint SOC real; se vuelve un valor genuino
en cuanto ARG-022 entregue ese cliente real.
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
# Sin cliente SOC real todavía (ARG-022): todo export es SOC_EMULATED. El
# día que exista un endpoint real autorizado, esto pasa a resolverse por
# configuración/entorno, nunca a un valor fijo que pueda mentir.
SOC_MODE = "SOC_EMULATED"


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
        "soc_mode": SOC_MODE,
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
        detail={
            "export_id": export_id,
            "case_id": case_id,
            "tlp": payload.tlp,
            "soc_mode": SOC_MODE,
            "status": record["status"],
        },
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


@router.post("/{case_id}/close")
def close_case(
    case_id: str,
    operator: Operator = Depends(get_current_operator),
    repos: Repositories = Depends(get_repositories),
    audit: AuditLog = Depends(get_audit_log),
) -> dict:
    """Cierre del caso (ARG-028, paquete "SOC handover": "...escalado y
    cierre"). Exige que el export MÁS RECIENTE del caso esté 'acked' — no
    tiene sentido cerrar un caso cuyo último envío nunca fue confirmado
    por el SOC, o que sigue en 'failed'. No se puede cerrar dos veces."""
    exports = repos.handovers.list_where(case_id=case_id)
    if not exports:
        raise HTTPException(status_code=404, detail=f"case {case_id!r} no tiene ningún export de handover")
    if repos.case_closures.get(case_id) is not None:
        raise HTTPException(status_code=409, detail=f"case {case_id!r} ya está cerrado")

    # El último de la lista, no max(..., key=created_at): InMemoryRepository
    # preserva orden de inserción (dict de Python) y dos exports creados en
    # sucesión rápida podrían compartir el mismo timestamp — el orden de
    # inserción es la señal fiable de "más reciente", la resolución del
    # reloj no lo es.
    latest = exports[-1]
    if latest["status"] != "acked":
        raise HTTPException(
            status_code=409,
            detail=f"no se puede cerrar: el export más reciente ({latest['export_id']}) está en estado '{latest['status']}', no 'acked'",
        )

    record = {
        "case_id": case_id,
        "closed_by": operator.subject,
        "closed_at": _now_iso(),
        "last_export_id": latest["export_id"],
    }
    repos.case_closures.add(record)
    audit.record(
        actor=operator.subject,
        action="handover.case.close",
        detail={"case_id": case_id, "last_export_id": latest["export_id"]},
    )
    return record


@router.get("/{case_id}/closure")
def get_case_closure(case_id: str, repos: Repositories = Depends(get_repositories)) -> dict:
    record = repos.case_closures.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"case {case_id!r} no está cerrado")
    return record
