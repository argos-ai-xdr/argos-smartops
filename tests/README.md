# tests

46 casos. Requieren `argos-contracts-scenarios` como hermano o `ARGOS_CONTRACTS_PATH` (ver `../docs/development.md`) — se saltan automáticamente si no lo encuentran.

| Carpeta | Contenido |
| --- | --- |
| `unit/` | Repositorio en memoria, transformación hechos/inferencias, `AuditLog` inmutable (incluye chequeo estructural de que no existe método de borrado), helpers de `plan_hash`/`signature_ref` |
| `api/` | Endpoints JSON vía `TestClient`: incidentes, aprobaciones (motivo/target/decisión inválidos), handover (export/ack/retry/historial) |
| `e2e/` | Flujo completo por la UI HTML real: cola → detalle → formulario → envío → auditoría; y aprobación → export de handover |
| `authorization/` | Rol incorrecto rechazado (403), autoaprobación rechazada, petición sin autenticar nunca devuelve 2xx |
| `accessibility/` | Chequeos reales sobre el HTML renderizado: `lang`, `<caption>`/`scope` en tablas, `<label for>` en cada campo del formulario, jerarquía de encabezados, `<title>` |
| `integration/` | Interoperabilidad real con `argos-cyber-tools`: una Approval emitida aquí debe ser aceptada por `policies.approval.ApprovalStore` de ese repo. Se salta si no está clonado como hermano de `argos-smartops` (mismo mecanismo que `contracts_path`) |

Ejecutar: `make test` o `pytest`.
