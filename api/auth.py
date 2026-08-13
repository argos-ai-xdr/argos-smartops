"""Identidad del operador autenticado + control de acceso por rol.

Sin Keycloak/OIDC desplegado todavía (ARG-022): `get_current_operator` es un
punto de extensión real (mismo patrón que `api.incidents.get_repositories`)
que la app de producción sobreescribirá con verificación real de token OIDC.
`require_role` sí es lógica real y probada hoy: rechaza con 403 a cualquier
operador sin el rol exacto exigido por la ruta.
"""
from __future__ import annotations

import dataclasses

from fastapi import Depends, HTTPException


@dataclasses.dataclass(frozen=True)
class Operator:
    subject: str
    role: str


def get_current_operator() -> Operator:  # pragma: no cover - sobreescrito con dependency_overrides
    raise RuntimeError("get_current_operator debe sobreescribirse al montar la app (ver api/app.py)")


def require_role(required_role: str):
    def _dependency(operator: Operator = Depends(get_current_operator)) -> Operator:
        if operator.role != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"rol '{required_role}' requerido, el operador tiene '{operator.role}'",
            )
        return operator

    return _dependency
