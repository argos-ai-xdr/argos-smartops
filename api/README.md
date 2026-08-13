# api/

| Módulo | Contenido | Lógica |
| --- | --- | --- |
| [`incidents.py`](incidents.py) | Cola + detalle, `facts`/`inferences` separados explícitamente | Real |
| [`recommendations.py`](recommendations.py) | Recomendaciones por incidente | Real |
| [`approvals.py`](approvals.py) | Creación de `Approval` — motivo, rol, confirmación de target, `plan_hash`/`signature_ref` compatibles con `argos-cyber-tools/policies/approval` | Real |
| [`actions.py`](actions.py) | Seguimiento de `ActionResult`, solo lectura | Real |
| [`evidence.py`](evidence.py) | Metadatos de `EvidenceManifest`, solo lectura | Real |
| [`handover.py`](handover.py) | Ciclo de vida del envío SOC: export/ack/retry/historial | Real (envío en sí simulado, ARG-022) |
| [`auth.py`](auth.py) | `Operator` + `require_role` — RBAC real; verificación OIDC real pendiente | Parcial |
| [`repository.py`](repository.py) | Repositorios en memoria sembrados con fixtures `smoke/` | Real |
| [`app.py`](app.py) | Factory de la app, monta todos los routers | Real |

`get_repositories` y `get_current_operator` son puntos de extensión (`Depends`) que la app de producción sobreescribe con clientes reales — los tests los sobreescriben con datos controlados.
