"""Cola de incidentes y detalle (P0). El detalle separa explícitamente
`facts` (lo observado: eventos, timeline, evidence_refs, entidades) de
`inferences` (lo derivado: técnicas ATT&CK, confidence) como claves de
nivel superior distintas en la respuesta — no una lista plana donde ambas
se mezclan, que es justo lo que el requisito P0 prohíbe.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.repository import Repositories

router = APIRouter(prefix="/incidents", tags=["incidents"])

# Mismo orden que argos-core/services/correlator._SEVERITY_ORDER (duplicado
# a propósito, mismo patrón que el resto de argos-ai-xdr).
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def to_queue_item(incident: dict) -> dict:
    return {
        "incident_id": incident["incident_id"],
        "severity": incident["severity"],
        "affected_assets": [e["id"] for e in incident.get("entities", []) if e.get("type") == "asset"],
        "status": "open",  # TODO (ARG-022): estado real desde el sistema, hoy no hay transición de estado modelada
        "observed_at": incident["observed_at"],
        "has_evidence": bool(incident.get("evidence_refs")),
    }


def to_incident_detail(incident: dict) -> dict:
    return {
        "incident_id": incident["incident_id"],
        "severity": incident["severity"],
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
    return [to_queue_item(i) for i in incidents]


@router.get("/{incident_id}")
def get_incident(incident_id: str, repos: Repositories = Depends(get_repositories)) -> dict:
    incident = repos.incidents.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"incidente {incident_id!r} no encontrado")
    return to_incident_detail(incident)
