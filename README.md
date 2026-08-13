# argos-smartops

Interfaz operacional para investigar incidentes, revisar recomendaciones, aprobar o rechazar acciones y generar el SOC handover. No ejecuta directamente herramientas — eso vive en `argos-cyber-tools`.

Parte de la organización [`argos-ai-xdr`](https://github.com/argos-ai-xdr). Arquitectura autoritativa y ADR en [`argos-control`](https://github.com/argos-ai-xdr/argos-control). Contratos y fixtures en [`argos-contracts-scenarios`](https://github.com/argos-ai-xdr/argos-contracts-scenarios).

## Stack

FastAPI + Jinja2 (server-rendered), **no React/TypeScript**. Es una decisión explícita del documento maestro v0.5: "React/TypeScript o una UI server-rendered ligera si la capacidad de 0,5 FTE no permite desarrollar el frontend completo" — con 0,5 FTE dedicado a SmartOps, server-rendered es lo defendible para el MVP. Autenticación Keycloak/OIDC (interfaz, sin Keycloak desplegado todavía). Autorización por rol. Telemetría OpenTelemetry (vía el mismo patrón de `argos-core/libs/argos_telemetry`, no reimplementado aquí).

## Contenido

| Carpeta | Contenido |
| --- | --- |
| `api/` | `incidents`, `recommendations`, `approvals`, `actions`, `evidence`, `handover` — routers FastAPI reales |
| `web/` | Plantillas Jinja2: cola de incidentes, detalle, aprobación |
| `packages/generated-contracts/` | Modelos Pydantic validados contra `argos-contracts-scenarios/schemas/` |
| `packages/ui-components/` | Macros Jinja2 y CSS compartidos |
| `deploy/` | Helm/Kustomize |
| `tests/` | `unit/`, `api/`, `e2e/`, `authorization/`, `accessibility/` |

## Funcionalidades P0

* **Cola de incidentes**: severidad, activos afectados, estado, técnicas ATT&CK, timestamps, evidencias disponibles.
* **Detalle del incidente**: timeline, hechos, inferencias **claramente diferenciadas**, activos y vulnerabilidades, fuentes CTI, evidencias.
* **Recomendación**: alternativas, impacto, incertidumbre, dependencias afectadas, resultado del dry-run, plan de rollback.
* **Aprobación HITL**: aprobar, rechazar, solicitar modificación; motivo obligatorio; rol del aprobador; TTL; visualización del `plan_hash`; confirmación explícita del target.
* **Seguimiento de acción**: estado, inicio/fin, recursos modificados, resultado de verificación, rollback, referencias de evidencia.
* **SOC handover**: TLP, campos permitidos, exportación, ACK, reintento, historial de exportaciones.

## Definition of Done

* Un analista puede revisar un incidente completo.
* La aplicación distingue hechos e inferencias.
* No se puede aprobar una acción modificada (mismo `plan_hash` que `argos-cyber-tools/policies/approval` exige).
* La aprobación incluye identidad, motivo y caducidad.
* La UI no almacena secretos.
* La UI no llama directamente al ejecutor.
* La auditoría es completa.
* El handover valida contra contrato.

Ver `docs/development.md`.
