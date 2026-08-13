"""Consulta de evidencia (P0), solo lectura — mismo contrato que
argos-contracts-scenarios/openapi/evidence-api.yaml. SmartOps nunca escribe
evidencia (ADR-006): esto expone metadatos (sha256, object_ref, retention),
nunca el contenido del artefacto.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.incidents import get_repositories
from api.repository import Repositories

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{artifact_id}")
def get_evidence_manifest(artifact_id: str, repos: Repositories = Depends(get_repositories)) -> dict:
    manifest = repos.evidence_manifests.get(artifact_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"artefacto {artifact_id!r} no encontrado")
    return {
        "artifact_id": manifest["artifact_id"],
        "media_type": manifest["media_type"],
        "object_ref": manifest["object_ref"],
        "sha256": manifest["sha256"],
        "created_at": manifest["created_at"],
        "retention": manifest["retention"],
    }
