"""Modelos Pydantic para la capa API/UI + validación real contra
argos-contracts-scenarios/schemas/. Los modelos Pydantic dan tipado y
documentación OpenAPI automática; la validación de schema real (esta
misma que ya usan argos-core y argos-cyber-tools) es lo que de verdad
garantiza que una respuesta cumple el contrato — Pydantic solo no basta,
porque no conoce las reglas cruzadas (allOf, anyOf) de los schemas reales.
"""
from __future__ import annotations

import json
import os
import pathlib

from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field
from referencing import Registry, Resource

CONTRACTS_ENV_VAR = "ARGOS_CONTRACTS_PATH"


class ContractsRepoNotFound(RuntimeError):
    pass


def resolve_contracts_path(start: pathlib.Path | None = None) -> pathlib.Path:
    env_value = os.environ.get(CONTRACTS_ENV_VAR)
    if env_value:
        path = pathlib.Path(env_value).expanduser().resolve()
        if not path.exists():
            raise ContractsRepoNotFound(f"{CONTRACTS_ENV_VAR}={env_value!r} no existe")
        return path

    base = start or pathlib.Path(__file__).resolve().parent.parent.parent
    sibling = (base.parent / "argos-contracts-scenarios").resolve()
    if sibling.exists():
        return sibling

    raise ContractsRepoNotFound(
        "No se encontró argos-contracts-scenarios. Clónalo como hermano de "
        f"este repositorio o define {CONTRACTS_ENV_VAR}."
    )


def build_registry(contracts_path: pathlib.Path) -> Registry:
    schemas_dir = contracts_path / "schemas"
    envelope_path = contracts_path / "envelope" / "v1" / "argos-envelope.schema.json"
    resources = []
    for path in list(schemas_dir.rglob("*.schema.json")) + [envelope_path]:
        data = json.loads(path.read_text(encoding="utf-8"))
        resources.append((path.as_uri(), Resource.from_contents(data)))
    return Registry().with_resources(resources)


def validate_payload(contracts_path: pathlib.Path, registry: Registry, contract: str, payload: dict) -> list[str]:
    schema_path = contracts_path / "schemas" / contract / "v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema = {**schema, "$id": schema_path.as_uri()}
    validator = Draft202012Validator(schema, registry=registry)
    return [e.message for e in validator.iter_errors(payload)]


class ContractValidationError(Exception):
    def __init__(self, contract: str, errors: list[str]):
        super().__init__(f"{contract} inválido: {errors}")
        self.contract = contract
        self.errors = errors


# --- Modelos de salida (envelope completo, tal como se sirven en la API) ---


class IncidentOut(BaseModel):
    id: str
    incident_id: str
    run_id: str
    severity: str
    confidence: str
    member_event_ids: list[str]
    timeline: list[dict]
    entities: list[dict]
    attack_techniques: list[str] = Field(default_factory=list)
    evidence_refs: list[str]


class RecommendationOut(BaseModel):
    id: str
    recommendation_id: str
    incident_id: str
    alternatives: list[dict]
    selected_action: str | None = None
    rationale_refs: list[str]
    impact: str
    uncertainty: str
    rollback_plan: str


class ApprovalCreate(BaseModel):
    """Lo que el operador envía desde la UI. approver_id NO viene en el
    body: lo asigna el servidor a partir de la sesión autenticada
    (web/auth/), para que un cliente no pueda autoasignarse como
    aprobador de su propia solicitud."""

    action_id: str
    decision: str = Field(pattern="^(APPROVE|REJECT)$")
    reason: str = Field(min_length=10, description="Motivo obligatorio, no un campo vacío o trivial")
    target_confirmed: bool = Field(description="El operador confirmó explícitamente el target antes de aprobar")


class ApprovalOut(BaseModel):
    id: str
    approval_id: str
    action_id: str
    approver_id: str
    role: str
    decision: str
    reason: str
    issued_at: str
    expires_at: str
    signature_ref: str


class ActionResultOut(BaseModel):
    id: str
    action_id: str
    idempotency_key: str
    dry_run: bool
    started_at: str
    status: str
    changed_resources: list[str]
    verification: dict
    rollback_ref: str | None = None


class EvidenceManifestOut(BaseModel):
    id: str
    artifact_id: str
    media_type: str
    object_ref: str
    sha256: str
    created_at: str
    retention: dict


class SOCHandoverOut(BaseModel):
    id: str
    case_id: str
    incident_summary: str
    timeline: list[dict]
    assets: list[str]
    residual_risk: str
    evidence_manifest_ref: str
    tlp: str
