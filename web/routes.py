"""UI server-rendered (Jinja2). Reutiliza la MISMA lógica de negocio que
`api/` — `submit_approval` llama a `api.approvals.create_approval`
directamente (no vía HTTP), así que la regla de negocio vive en un solo
sitio; esta capa solo traduce HTML↔objetos.

`action_id` del formulario es el `decision_id` del PolicyDecision real
asociado a la recomendación (mismo `run_id`, ver api/repository.py) — no
`recommendation_id`. Sin argos-cyber-tools desplegado todavía (ARG-022) no
hay un cliente HTTP que lo resuelva remotamente, así que se busca en el
repositorio local sembrado con las mismas fixtures/smoke/; el mecanismo de
lookup (por run_id compartido) es el mismo que usará ese cliente real.
"""
from __future__ import annotations

import pathlib

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from generated_contracts import ApprovalCreate

from api.approvals import create_approval
from api.audit import AuditLog, get_audit_log
from api.auth import Operator, get_current_operator
from api.incidents import get_repositories, to_incident_detail, to_queue_item
from api.recommendations import to_recommendation_view
from api.repository import Repositories

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))


@router.get("/incidents", response_class=HTMLResponse)
def incidents_queue_page(request: Request, repos: Repositories = Depends(get_repositories)) -> HTMLResponse:
    incidents = [to_queue_item(i) for i in repos.incidents.list_all()]
    return templates.TemplateResponse(request, "incidents_queue.html", {"incidents": incidents})


@router.get("/incidents/{incident_id}", response_class=HTMLResponse)
def incident_detail_page(request: Request, incident_id: str, repos: Repositories = Depends(get_repositories)) -> HTMLResponse:
    incident = repos.incidents.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"incidente {incident_id!r} no encontrado")
    return templates.TemplateResponse(request, "incident_detail.html", {"incident": to_incident_detail(incident)})


@router.get("/incidents/{incident_id}/approve", response_class=HTMLResponse)
def approval_form_page(request: Request, incident_id: str, repos: Repositories = Depends(get_repositories)) -> HTMLResponse:
    matches = repos.recommendations.list_where(incident_id=incident_id)
    if not matches:
        raise HTTPException(status_code=404, detail=f"sin recomendación para el incidente {incident_id!r}")
    raw_recommendation = matches[0]

    decisions = repos.policy_decisions.list_where(run_id=raw_recommendation["run_id"])
    if not decisions:
        raise HTTPException(
            status_code=404,
            detail=f"sin PolicyDecision para run_id={raw_recommendation['run_id']!r} — ver docstring del módulo",
        )

    recommendation = to_recommendation_view(raw_recommendation)
    return templates.TemplateResponse(
        request,
        "approval_form.html",
        {
            "incident_id": incident_id,
            "recommendation": recommendation,
            "action_id": decisions[0]["decision_id"],  # ver docstring del módulo
        },
    )


@router.post("/incidents/{incident_id}/approve")
def submit_approval(
    incident_id: str,
    decision: str = Form(...),
    reason: str = Form(...),
    target_confirmed: str = Form(...),
    action_id: str = Form(...),
    operator: Operator = Depends(get_current_operator),
    repos: Repositories = Depends(get_repositories),
    audit: AuditLog = Depends(get_audit_log),
) -> RedirectResponse:
    payload = ApprovalCreate(
        action_id=action_id,
        decision=decision,
        reason=reason,
        target_confirmed=(target_confirmed == "true"),
    )
    approval = create_approval(payload, operator=operator, repos=repos)
    audit.record(
        actor=operator.subject,
        action="approval.create",
        detail={"approval_id": approval["approval_id"], "decision": decision, "incident_id": incident_id},
    )
    return RedirectResponse(f"/incidents/{incident_id}", status_code=303)
