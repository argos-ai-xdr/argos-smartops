"""Factory de la app FastAPI. `repositories` es inyectable para que los
tests puedan pasar datos controlados en vez de los fixtures smoke/ por
defecto — mismo principio que el resto de argos-ai-xdr: nada hardcodeado
que impida sustituir la fuente de datos real más adelante (ARG-022).
"""
from __future__ import annotations

import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api import actions, approvals, evidence, handover, incidents, recommendations
from api.incidents import get_repositories
from api.repository import Repositories, build_empty_repositories
from web import routes as web_routes
from web.audit import AuditLog

STATIC_DIR = pathlib.Path(__file__).resolve().parent.parent / "packages" / "ui_components" / "static"


def create_app(
    repositories: Repositories | None = None,
    audit_log: AuditLog | None = None,
) -> FastAPI:
    app = FastAPI(title="argos-smartops")
    repos = repositories or build_empty_repositories()
    audit = audit_log or AuditLog()

    app.state.repositories = repos
    app.state.audit_log = audit
    app.dependency_overrides[get_repositories] = lambda: repos
    app.dependency_overrides[web_routes.get_audit_log] = lambda: audit

    # Prefijo /api obligatorio: sin él, api.incidents y web.routes registran
    # ambos GET /incidents/{incident_id} (uno JSON, otro HTML) en la misma
    # ruta — FastAPI resuelve por orden de include_router y el segundo
    # nunca se alcanza. Encontrado probando la UI de verdad, no leyendo el
    # código: la petición devolvía 200 pero con JSON en vez de HTML.
    app.include_router(incidents.router, prefix="/api")
    app.include_router(recommendations.router, prefix="/api")
    app.include_router(actions.router, prefix="/api")
    app.include_router(evidence.router, prefix="/api")
    app.include_router(approvals.router, prefix="/api")
    app.include_router(handover.router, prefix="/api")
    app.include_router(web_routes.router)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # api.auth.get_current_operator NO se sobreescribe aquí a propósito: sin
    # Keycloak/OIDC real (ARG-022), la app DEBE fallar si nadie lo
    # sobreescribe explícitamente, en vez de dejar pasar peticiones sin
    # identidad verificada. Los tests y el entorno de desarrollo lo hacen vía
    # `app.dependency_overrides[get_current_operator] = ...`.
    return app
