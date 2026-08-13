# api/

| Módulo | Contenido | Lógica |
| --- | --- | --- |
| [`incidents.py`](incidents.py) | Cola + detalle, `facts`/`inferences` separados explícitamente | Real |
| [`recommendations.py`](recommendations.py) | Recomendaciones por incidente | Real |
| [`approvals.py`](approvals.py) | Creación de `Approval` — motivo, rol, confirmación de target, `plan_hash`/`signature_ref` compatibles con `argos-cyber-tools/policies/approval` | Real |
| [`actions.py`](actions.py) | Seguimiento de `ActionResult`, solo lectura | Real |
| [`evidence.py`](evidence.py) | Metadatos de `EvidenceManifest`, solo lectura | Real |
| [`handover.py`](handover.py) | Ciclo de vida del envío SOC: export/ack/retry/historial, exige operador autenticado y queda en `AuditLog` | Real (envío en sí simulado, ARG-022) |
| [`auth.py`](auth.py) | `Operator` + `require_role` — RBAC real; verificación OIDC real pendiente | Parcial |
| [`audit.py`](audit.py) | `AuditLog` real e inmutable — sin método de borrado/modificación | Real |
| [`repository.py`](repository.py) | Repositorios en memoria sembrados con fixtures `smoke/` | Real |
| [`app.py`](app.py) | Factory de la app, monta todos los routers | Real |

`get_repositories`, `get_current_operator` y `get_audit_log` son puntos de extensión (`Depends`) que la app de producción sobreescribe con clientes reales — los tests los sobreescriben con datos controlados.

`auth.py` y `audit.py` viven en `api/`, no en `web/`, aunque el bootstrap original los puso ahí: en cuanto un segundo consumidor (`api/handover.py`) necesitó cualquiera de los dos directamente, dejarlos bajo `web/` habría invertido la dependencia (`web/` ya depende de `api/`, no al revés) — ver la nota de estructura en [`../web/README.md`](../web/README.md).
