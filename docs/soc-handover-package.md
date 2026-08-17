# Paquete SOC handover (ARG-028)

ARG-028 (S8, propuesta v0.6.25.4 §16.7) define el paquete **"SOC
handover: Schema, TLP/clasificación, redacción, mapping, ACK/retry/dedupe,
escalado y cierre"**, validado por "Consumer conformance/tabletop". Este
documento describe el estado real de cada pieza — la mayoría existe y
está probada; dos (`escalado`, en parte `dedupe`) no, y se documentan
como gap real, no se fingen.

## Schema

Contrato `soc-handover/v1` (`argos-contracts-scenarios/schemas/soc-handover/`)
— campos obligatorios: `case_id`, `incident_summary`, `timeline`, `assets`,
`residual_risk`, `evidence_manifest_ref`, `tlp`. Opcionales:
`attack_techniques`, `iocs`, `actions`.

## TLP / clasificación / redacción / mapping

**Real, en `argos-core/services/soc_adapter/__init__.py`**, no en este
repo (`argos-smartops` gestiona el ESTADO del envío, no la construcción
del contenido):

* `SOCAdapter.build_handover(...)` es el MAPPING de `Incident` →
  `SOCHandover`: `case_id` nuevo, `incident_summary` derivado de
  `incident_id`+`severity`, `timeline` copiado, `assets` extraído de
  `entities` filtrando `type=="asset"`, y los campos opcionales solo si
  el incidente los trae.
* `redact_for_tlp(payload, tlp)` es la REDACCIÓN real por nivel — nunca
  muta el original (el evidence store conserva la versión sin redactar;
  solo la copia exportada se filtra):
  * `RED`: `incident_summary` se sustituye por un aviso fijo, cada
    `timeline` entry pierde su `description`, y ningún campo opcional
    (`actions`/`attack_techniques`/`iocs`) se incluye.
  * `AMBER`: añade `actions`.
  * `GREEN`: añade también `attack_techniques`.
  * `CLEAR`: añade también `iocs` (los cuatro opcionales).
  * Los campos OBLIGATORIOS del schema nunca se eliminan (quitarlos
    rompería la validación) — la redacción actúa sobre su CONTENIDO
    (`RED`) o sobre los opcionales, nunca sobre la forma del contrato.

## ACK / retry / dedupe

**Real, en `argos-smartops/api/handover.py`**:

* `POST /{case_id}/export` → `status=sent` (o `failed` si
  `simulate_failure=true`, hook de desarrollo documentado en el propio
  módulo).
* `POST /exports/{export_id}/ack` → `sent → acked`; `409` si el export
  no está en `sent` (no se puede confirmar algo que nunca se envió, ni
  volver a confirmar algo ya confirmado).
* `POST /exports/{export_id}/retry` → `failed → sent`, incrementa
  `attempts`; `409` si no está en `failed`.
* **Dedupe**: parcial. `export_id = f"exp-{case_id}-{uuid4().hex[:12]}"`
  (no un contador) evita que dos exports del MISMO caso en la misma
  ventana de carrera colisionen y se pisen en el repositorio en memoria
  (bug real, mismo patrón corregido en `api/approvals.py`) — eso es
  deduplicación de IDENTIFICADORES. Lo que NO existe: deduplicación
  semántica (detectar que dos exports son "el mismo" caso reenviado sin
  cambios y fusionarlos/rechazarlos). No se fabrica esa lógica sin un
  criterio real de "qué hace a dos exports duplicados" que el documento
  no define.

Cada transición exige un operador autenticado y queda en `AuditLog`
(`handover.export.create`/`.ack`/`.retry`) — encontrado ejecutando la app
sin token: `/export` devolvía `201` para cualquiera.

`SOC_MODE` (constante `SOC_EMULATED`) va en cada registro y en el
`AuditLog` — sin endpoint SOC real todavía (ARG-022), nunca se afirma
`SOC_REAL`.

## Cierre

**Real, añadido en esta sesión**: `POST /{case_id}/close`
(`api/handover.py`). Exige que el export MÁS RECIENTE del caso (por
orden de inserción, no por timestamp — dos exports creados en sucesión
rápida podrían compartir el mismo `created_at`) esté `acked`; `404` si el
caso no tiene ningún export; `409` si ya está cerrado o si el export más
reciente no está `acked`. Registra `closed_by`/`closed_at`/`last_export_id`
en un repositorio propio (`case_closures`, separado de `handovers` porque
el cierre es una propiedad del CASO, no de un export individual) y en
`AuditLog` (`handover.case.close`). Consulta: `GET /{case_id}/closure`
(`404` si no está cerrado).

## Escalado

**No existe.** No hay código de escalado de CASOS en ningún repo —
`argos-cyber-tools/graph/escalation.py` sí existe, pero es "privilege
escalation" del grafo RBAC (ARG-012, C-07), un concepto de seguridad
completamente distinto, no aplicable aquí. A diferencia de `break-glass`
(que sí tiene una
definición formal en el documento, reservada a v0.6.26 — ver
`operator-package.md`), "escalado" en el contexto de SOC handover no
tiene una definición operativa en ningún artefacto del repo: ¿escalar a
quién? ¿qué cambia (severidad, owner, canal)? Inventar esa semántica
aquí sería tomar una decisión de diseño real sin la autoridad ni el
contexto para hacerlo bien — se deja como gap explícito, pendiente de
una definición real antes de poder construirse.
