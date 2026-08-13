from __future__ import annotations

from api.audit import AuditLog


def test_record_appends_and_returns_entry():
    log = AuditLog()
    entry = log.record(actor="soc-1", action="approval.create", detail={"x": 1})
    assert entry.actor == "soc-1"
    assert log.all() == (entry,)


def test_all_returns_immutable_snapshot():
    log = AuditLog()
    log.record(actor="a", action="x", detail={})
    snapshot = log.all()
    log.record(actor="b", action="y", detail={})
    assert len(snapshot) == 1  # el snapshot anterior no ve la entrada nueva
    assert len(log.all()) == 2


def test_for_actor_filters():
    log = AuditLog()
    log.record(actor="a", action="x", detail={})
    log.record(actor="b", action="y", detail={})
    log.record(actor="a", action="z", detail={})
    assert len(log.for_actor("a")) == 2


def test_audit_log_has_no_delete_or_modify_method():
    """Chequeo estructural: la auditoría es append-only por diseño, no por
    convención — no existe ningún método para borrar o reescribir."""
    forbidden_method_names = {"delete", "remove", "clear", "update", "modify", "edit"}
    actual_methods = {name for name in dir(AuditLog) if not name.startswith("_")}
    assert not (forbidden_method_names & actual_methods)
