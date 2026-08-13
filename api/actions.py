"""Seguimiento de acción (P0): estado, inicio/fin, recursos modificados,
verificación, rollback, referencias de evidencia. Solo lectura — SmartOps
no ejecuta ni revierte, eso lo hace argos-cyber-tools.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.incidents import get_repositories
from api.repository import Repositories

router = APIRouter(prefix="/actions", tags=["actions"])


def to_action_view(action_result: dict) -> dict:
    return {
        "action_id": action_result["action_id"],
        "status": action_result["status"],
        "dry_run": action_result["dry_run"],
        "started_at": action_result["started_at"],
        "ended_at": action_result.get("ended_at"),
        "changed_resources": action_result.get("changed_resources", []),
        "verification": action_result.get("verification"),
        "rollback_ref": action_result.get("rollback_ref"),
        "evidence_refs": action_result.get("evidence_refs", []),
    }


@router.get("/{action_id}")
def get_action(action_id: str, repos: Repositories = Depends(get_repositories)) -> dict:
    action_result = repos.action_results.get(action_id)
    if action_result is None:
        raise HTTPException(status_code=404, detail=f"acción {action_id!r} no encontrada")
    return to_action_view(action_result)
