from __future__ import annotations

from api.repository import InMemoryRepository, build_empty_repositories, build_seeded_repositories


def test_seeded_repositories_load_real_fixtures(contracts_path):
    repos = build_seeded_repositories(contracts_path)
    assert repos.incidents.list_all()
    assert repos.recommendations.list_all()
    assert repos.policy_decisions.list_all()
    assert repos.action_results.list_all()
    assert repos.evidence_manifests.list_all()
    assert repos.approvals.list_all() == []  # nadie ha aprobado nada todavía
    assert repos.handovers.list_all() == []


def test_empty_repositories_start_with_nothing():
    repos = build_empty_repositories()
    assert repos.incidents.list_all() == []


def test_in_memory_repository_add_and_get():
    repo = InMemoryRepository(key_field="id")
    repo.add({"id": "a", "value": 1})
    assert repo.get("a") == {"id": "a", "value": 1}
    assert repo.get("missing") is None


def test_in_memory_repository_list_where_filters():
    repo = InMemoryRepository(key_field="id")
    repo.add({"id": "a", "owner": "x"})
    repo.add({"id": "b", "owner": "y"})
    repo.add({"id": "c", "owner": "x"})
    assert {item["id"] for item in repo.list_where(owner="x")} == {"a", "c"}


def test_add_with_same_key_overwrites():
    repo = InMemoryRepository(key_field="id")
    repo.add({"id": "a", "value": 1})
    repo.add({"id": "a", "value": 2})
    assert repo.get("a")["value"] == 2
    assert len(repo.list_all()) == 1
