"""Repositorios en memoria, reales (no mocks): guardan y devuelven los
mismos dicts validados contra schema que produciría argos-core en
producción. Sembrados por defecto con los fixtures smoke/ de
argos-contracts-scenarios para poder desarrollar y probar sin desplegar el
resto del sistema (ARG-022 los sustituirá por clientes HTTP/NATS reales).
"""
from __future__ import annotations

import dataclasses
import json
import pathlib


@dataclasses.dataclass
class InMemoryRepository:
    """Guarda dicts por su clave primaria (`key_field`). No valida contra
    schema en escritura — quien construye el payload (api/approvals.py,
    etc.) ya lo hizo antes de guardarlo aquí."""

    key_field: str
    _items: dict[str, dict] = dataclasses.field(default_factory=dict)

    def add(self, item: dict) -> None:
        self._items[item[self.key_field]] = item

    def get(self, key: str) -> dict | None:
        return self._items.get(key)

    def list_all(self) -> list[dict]:
        return list(self._items.values())

    def list_where(self, **filters: str) -> list[dict]:
        return [item for item in self._items.values() if all(item.get(k) == v for k, v in filters.items())]


@dataclasses.dataclass
class Repositories:
    incidents: InMemoryRepository
    recommendations: InMemoryRepository
    approvals: InMemoryRepository
    action_results: InMemoryRepository
    evidence_manifests: InMemoryRepository
    handovers: InMemoryRepository


def _load_fixture(contracts_path: pathlib.Path, contract: str, filename: str) -> dict:
    path = contracts_path / "fixtures" / "smoke" / contract / filename
    return json.loads(path.read_text(encoding="utf-8"))


def build_seeded_repositories(contracts_path: pathlib.Path) -> Repositories:
    incidents = InMemoryRepository(key_field="incident_id")
    incidents.add(_load_fixture(contracts_path, "incident", "incident-001.json"))

    recommendations = InMemoryRepository(key_field="recommendation_id")
    recommendations.add(_load_fixture(contracts_path, "recommendation", "recommendation-001.json"))

    action_results = InMemoryRepository(key_field="action_id")
    action_results.add(_load_fixture(contracts_path, "action-result", "action-result-001.json"))

    evidence_manifests = InMemoryRepository(key_field="artifact_id")
    evidence_manifests.add(_load_fixture(contracts_path, "evidence-manifest", "evidence-manifest-001.json"))

    return Repositories(
        incidents=incidents,
        recommendations=recommendations,
        approvals=InMemoryRepository(key_field="approval_id"),  # vacío: las aprobaciones las crea el operador
        action_results=action_results,
        evidence_manifests=evidence_manifests,
        handovers=InMemoryRepository(key_field="export_id"),  # vacío: los exports los crea api/handover
    )


def build_empty_repositories() -> Repositories:
    """Para tests que quieren control total sobre los datos, sin fixtures."""
    return Repositories(
        incidents=InMemoryRepository(key_field="incident_id"),
        recommendations=InMemoryRepository(key_field="recommendation_id"),
        approvals=InMemoryRepository(key_field="approval_id"),
        action_results=InMemoryRepository(key_field="action_id"),
        evidence_manifests=InMemoryRepository(key_field="artifact_id"),
        handovers=InMemoryRepository(key_field="export_id"),
    )
