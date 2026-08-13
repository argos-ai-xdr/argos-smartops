"""Vista de recomendación (P0): alternativas, impacto, incertidumbre,
plan de rollback. dependencies_affected se deriva de rationale_refs — el
propio contrato Recommendation no tiene un campo de dependencias separado
todavía (ver argos-contracts-scenarios/schemas/recommendation/), así que se
documenta explícitamente en vez de inventar un campo que no existe.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.incidents import get_repositories
from api.repository import Repositories

router = APIRouter(tags=["recommendations"])


def to_recommendation_view(recommendation: dict) -> dict:
    return {
        "recommendation_id": recommendation["recommendation_id"],
        "incident_id": recommendation["incident_id"],
        "alternatives": recommendation["alternatives"],
        "selected_action": recommendation.get("selected_action"),
        "impact": recommendation["impact"],
        "uncertainty": recommendation["uncertainty"],
        "rollback_plan": recommendation["rollback_plan"],
        "affected_dependencies_refs": recommendation.get("rationale_refs", []),
    }


@router.get("/incidents/{incident_id}/recommendations")
def list_recommendations_for_incident(incident_id: str, repos: Repositories = Depends(get_repositories)) -> list[dict]:
    matches = repos.recommendations.list_where(incident_id=incident_id)
    return [to_recommendation_view(r) for r in matches]


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: str, repos: Repositories = Depends(get_repositories)) -> dict:
    recommendation = repos.recommendations.get(recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail=f"recomendación {recommendation_id!r} no encontrada")
    return to_recommendation_view(recommendation)
