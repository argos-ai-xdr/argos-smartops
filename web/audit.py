"""Auditoría real e inmutable: cada aprobación/rechazo y cada export de
handover queda registrado. `AuditLog` no expone ningún método de borrado o
modificación a propósito — la única forma de "corregir" un registro es
añadir uno nuevo que lo explique, nunca reescribir el histórico.
"""
from __future__ import annotations

import dataclasses
import datetime
import uuid


@dataclasses.dataclass(frozen=True)
class AuditEntry:
    entry_id: str
    actor: str
    action: str
    detail: dict
    timestamp: str


class AuditLog:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, *, actor: str, action: str, detail: dict) -> AuditEntry:
        entry = AuditEntry(
            entry_id=f"audit-{uuid.uuid4().hex[:12]}",
            actor=actor,
            action=action,
            detail=detail,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        self._entries.append(entry)
        return entry

    def all(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)  # copia inmutable — modificar el resultado no afecta al log

    def for_actor(self, actor: str) -> tuple[AuditEntry, ...]:
        return tuple(e for e in self._entries if e.actor == actor)
