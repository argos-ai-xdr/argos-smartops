"""Cola de incidentes y detalle (P0). El detalle separa explícitamente
`facts` (lo observado: eventos, timeline, evidence_refs, entidades) de
`inferences` (lo derivado: técnicas ATT&CK, confidence) como claves de
nivel superior distintas en la respuesta — no una lista plana donde ambas
se mezclan, que es justo lo que el requisito P0 prohíbe.

`status` (open/investigating/closed) NO es parte del contrato `Incident`
v1 — el schema real no tiene ese campo, y `timeline` se documenta
explícitamente como "Inmutable una vez emitido". Es estado operativo del
ANALISTA, seguido aparte en `repos.incident_status` (mismo patrón que
`case_closures` en `api/handover.py`: el registro inmutable del sistema y
el estado de trabajo del operador viven en repositorios separados). Antes
de esta sesión estaba fijado siempre a `"open"` sin ninguna transición
real (ver el historial de `to_queue_item`) — un incidente ya cerrado
seguía apareciendo como abierto en la cola indefinidamente.
"""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.audit import AuditLog, get_audit_log
from api.auth import Operator, get_current_operator
from api.repository import Repositories

router = APIRouter(prefix="/incidents", tags=["incidents"])

# Mismo orden que argos-core/services/correlator._SEVERITY_ORDER (duplicado
# a propósito, mismo patrón que el resto de argos-ai-xdr).
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

_DEFAULT_STATUS = "open"
_VALID_STATUSES = {"open", "investigating", "closed"}
# Transiciones permitidas — un incidente closed no pasa a investigating
# sin volver a abrirse primero (evita un estado intermedio ambiguo sobre
# si sigue cerrado o no).
_ALLOWED_TRANSITIONS = {
    "open": {"investigating", "closed"},
    "investigating": {"open", "closed"},
    "closed": {"open"},
}


class StatusUpdate(BaseModel):
    status: str


def current_incident_status(repos: Repositories, incident_id: str) -> str:
    record = repos.incident_status.get(incident_id)
    return record["status"] if record else _DEFAULT_STATUS


def to_queue_item(incident: dict, *, status: str) -> dict:
    return {
        "incident_id": incident["incident_id"],
        "severity": incident["severity"],
        "affected_assets": [e["id"] for e in incident.get("entities", []) if e.get("type") == "asset"],
        "status": status,
        "observed_at": incident["observed_at"],
        "has_evidence": bool(incident.get("evidence_refs")),
    }


def to_incident_detail(incident: dict, *, status: str) -> dict:
    return {
        "incident_id": incident["incident_id"],
        "severity": incident["severity"],
        "status": status,
        "facts": {
            "member_event_ids": incident["member_event_ids"],
            "timeline": incident["timeline"],
            "evidence_refs": incident["evidence_refs"],
            "entities": incident["entities"],
        },
        "inferences": {
            "attack_techniques": incident.get("attack_techniques", []),
            "confidence": incident["confidence"],
        },
    }


def get_repositories() -> Repositories:  # pragma: no cover - sobreescrito con dependency_overrides (ver api/app.py)
    raise RuntimeError("get_repositories debe sobreescribirse al montar la app (ver api/app.py)")


@router.get("")
def list_incidents(repos: Repositories = Depends(get_repositories)) -> list[dict]:
    # web/templates/incidents_queue.html anuncia "ordenados por severidad" en
    # su <caption> — list_all() devuelve orden de inserción, no severidad;
    # sin esto un analista vería incidentes low/medium por delante de un
    # critical solo por haberse cargado antes (bug real: la UI prometía un
    # orden que el endpoint nunca aplicaba).
    incidents = sorted(
        repos.incidents.list_all(),
        key=lambda i: _SEVERITY_ORDER.get(i.get("severity", "low"), 0),
        reverse=True,
    )
    return [to_queue_item(i, status=current_incident_status(repos, i["incident_id"])) for i in incidents]


@router.get("/{incident_id}")
def get_incident(incident_id: str, repos: Repositories = Depends(get_repositories)) -> dict:
    incident = repos.incidents.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"incidente {incident_id!r} no encontrado")
    return to_incident_detail(incident, status=current_incident_status(repos, incident_id))


@router.post("/{incident_id}/status")
def update_incident_status(
    incident_id: str,
    payload: StatusUpdate,
    operator: Operator = Depends(get_current_operator),
    repos: Repositories = Depends(get_repositories),
    audit: AuditLog = Depends(get_audit_log),
) -> dict:
    if repos.incidents.get(incident_id) is None:
        raise HTTPException(status_code=404, detail=f"incidente {incident_id!r} no encontrado")
    if payload.status not in _VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"status inválido: {payload.status!r}, debe ser uno de {sorted(_VALID_STATUSES)}")

    current = current_incident_status(repos, incident_id)
    if payload.status == current:
        raise HTTPException(status_code=409, detail=f"el incidente ya está en estado {current!r}")
    if payload.status not in _ALLOWED_TRANSITIONS[current]:
        raise HTTPException(
            status_code=409,
            detail=f"transición no permitida: {current!r} -> {payload.status!r} (permitidas desde {current!r}: {sorted(_ALLOWED_TRANSITIONS[current])})",
        )

    record = {
        "incident_id": incident_id,
        "status": payload.status,
        "updated_by": operator.subject,
        "updated_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    repos.incident_status.add(record)
    audit.record(
        actor=operator.subject,
        action="incident.status.update",
        detail={"incident_id": incident_id, "from": current, "to": payload.status},
    )
    return record
