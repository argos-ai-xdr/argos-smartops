from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient
from generated_contracts import ContractsRepoNotFound, resolve_contracts_path

from api.app import create_app
from api.auth import Operator, get_current_operator
from api.repository import build_seeded_repositories
from web.audit import AuditLog


@pytest.fixture(scope="session")
def contracts_path() -> pathlib.Path:
    try:
        return resolve_contracts_path()
    except ContractsRepoNotFound as exc:
        pytest.skip(str(exc))


@pytest.fixture
def audit_log() -> AuditLog:
    return AuditLog()


@pytest.fixture
def app(contracts_path, audit_log):
    repos = build_seeded_repositories(contracts_path)
    return create_app(repos, audit_log)


@pytest.fixture
def approver_client(app):
    app.dependency_overrides[get_current_operator] = lambda: Operator(subject="soc-1", role="soc-approver")
    return TestClient(app)


@pytest.fixture
def unauthenticated_client(app):
    """Sin override de get_current_operator: cualquier ruta que dependa de
    identidad debe fallar, no servir con un operador implícito."""
    return TestClient(app, raise_server_exceptions=False)
