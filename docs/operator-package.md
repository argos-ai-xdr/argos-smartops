# Paquete operador/SOC — HITL/SOAR (ARG-028)

ARG-028 (S8, propuesta v0.6.25.4 §16.7) asigna a `argos-smartops` el
paquete **"HITL/SOAR: Policy, approve/reject/expire, action, verify,
rollback, break-glass y segregación"**, validado por un "ejercicio
approve/reject/rollback" — y en su desglose por repositorio (§16.8) fija
el artefacto final de este repo como **"operator/SOC package"**. Este
documento es esa pieza: describe el flujo REAL, tal como existe hoy en
código y probado, no un diseño aspiracional.

**break-glass queda fuera de este documento a propósito** — ver la
sección final.

## 1. Flujo completo, con el archivo real que implementa cada paso

```
PolicyDecision (argos-cyber-tools, OPA)
        │
        ▼
POST /approvals  (argos-smartops, api/approvals.py)
  approve/reject
        │
        ▼
Gateway.authorize() (argos-cyber-tools, mcp_gateway)
  valida approval antes de permitir "execute"
        │
        ▼
Executor  (argos-cyber-tools, executors/kubernetes.py |
           executors/scale_to_zero.py)
  action + verify
        │
        ▼ (si falla verificación o se activa el kill switch)
rollback.strategies  (argos-cyber-tools)
  rollback + verify independiente
```

## 2. Policy

`argos-cyber-tools/mcp_gateway.Gateway.authorize()` es la autoridad real
que decide si un `execute` procede — no un stub. Antes de llegar a
Approval, ya aplica: `target_allowlist` por tool
(`policies/target-allowlists/*.yaml`), `required_scope` del
`tool_catalog/definitions/*.yaml`, y el modo (`dry-run`/`execute`)
declarado por la tool. Probado en `argos-cyber-tools/tests/authorization/test_gateway.py`
y en los 5 casos reales de `tests/graph/test_attack_path.py` (incluye el
caso `GATE_BYPASSED` real de `increase_monitoring`, ver
`runbooks/README.md`).

## 3. Approve / Reject / Expire

**Un único endpoint**, no tres: `POST /approvals` (`api/approvals.py`),
`decision` en `{APPROVE, REJECT}` (`ApprovalCreate.decision`, patrón
regex `^(APPROVE|REJECT)$` — un tercer valor es rechazado por Pydantic
antes de llegar a lógica de negocio).

* **Rol exigido**: `soc-approver` (`require_role`, único rol real
  reconocido hoy — ver `runbooks/*.md` de argos-cyber-tools para la
  misma cita).
* **`target_confirmed=true` obligatorio**: el operador debe confirmar el
  target explícitamente antes de que el servidor acepte la aprobación
  (`HTTPException 400` si falta).
* **Segregación de funciones en el momento de crear la Approval**:
  `operator.subject == REQUESTER_SYSTEM_ID` → `403` (un
  aprobador no puede ser el sistema que generó la Recommendation).
* **`plan_hash`**: se calcula a partir del `PolicyDecision` real
  (`tool`/`target`/`action`/`params`) que `action_id` referencia — NO de
  `(action_id, decision)`. Bug real encontrado y corregido ejecutando
  ambos repos juntos (`argos-smartops` emisor + `argos-cyber-tools`
  validador): con la fórmula vieja, la Approval SIEMPRE se rechazaba con
  un mensaje engañoso ("la acción cambió después de aprobarse") aunque
  nada hubiera cambiado — las dos fórmulas nunca coincidían. Ver
  `tests/integration/test_cross_repo_approval_interop.py`.
* **`approval_id`**: `uuid4`, no un contador — dos aprobaciones de la
  misma acción en el mismo segundo no colisionan (bug real, mismo patrón
  que `handover.py`, ver su docstring).
* **TTL ("expire")**: `APPROVAL_TTL_MINUTES = 15` (constante real en
  `api/approvals.py`) fija `expires_at` al emitir. No hay un endpoint
  `/expire` activo — la caducidad se comprueba pasivamente en el momento
  de consumir la Approval (`argos-cyber-tools/policies/approval.ApprovalStore.validate_and_consume`:
  `if now > expires_at: raise ApprovalRejected`).

`argos-cyber-tools` **revalida todo esto de forma independiente** antes
de ejecutar nada (ADR-011) — lo de `argos-smartops` reduce aprobaciones
inválidas por error humano en la UI, no es el control de seguridad final.
Ver `ApprovalStore.validate_and_consume`: rechaza replay (`approval_id`
ya consumida), segregación (`approver_id == requester_id` **o**
`== executor_id`), `decision != APPROVE`, TTL expirado, y `signature_ref`
que no coincide con el `plan_hash` recalculado en el momento de ejecutar
— en ese orden, y solo marca la Approval como consumida si TODAS pasan.

## 4. Action / Verify / Rollback

Documentado en detalle, herramienta por herramienta, en
`argos-cyber-tools/runbooks/{isolate_kubernetes_workload,scale_to_zero}.md`
— no se duplica aquí. Resumen: cada acción produce un `ActionResult` real
validado contra el schema `action-result/v1` antes de devolverse
(`InvalidActionResult` si no valida), con `verification.passed`
recalculado de forma independiente tras cualquier rollback
(`rollback/verification.py`), y `idempotency_key` obligatoria
(`IdempotencyStore`, un reintento nunca reaplica el efecto).

## 5. Verificación cruzada de plan_hash — ejercicio reproducible

`test_cross_repo_approval_interop.py` (`argos-smartops/tests/integration/`)
es el ejercicio real de interoperabilidad que sostiene la afirmación de
la sección 3: usa `api.approvals.compute_plan_hash`/`compute_signature_ref`
(las MISMAS funciones que usa el endpoint `POST /approvals`, no una
reescritura) para construir una `Approval`, y la valida con el
`ApprovalStore` REAL de `argos-cyber-tools` importado como módulo hermano
(no un doble reescrito) — así es como se encontró el bug de `plan_hash`
descrito arriba. No invoca el endpoint HTTP en sí (eso lo cubren
`tests/api/test_approvals_api.py` y `tests/authorization/test_gateway.py`
por separado); prueba la interoperabilidad del CÁLCULO entre los dos
repos, que es donde estaba el bug real. Reproducible con:

```
pytest tests/integration/test_cross_repo_approval_interop.py -v
```

## 6. Segregación de funciones

Matriz completa en `argos-control/governance/policies/segregation-of-duties.md`
(regla base: "quien genera una recomendación o ejecuta un playbook no
puede autoaprobarla; QA/Security Observer puede bloquear un gate; ningún
rol puede aprobar su propia excepción de seguridad"). Aplicación técnica
real, no solo documental:

* `api/approvals.py`: `operator.subject == REQUESTER_SYSTEM_ID` → `403`.
* `ApprovalStore.validate_and_consume`: `approver_id == requester_id` **o**
  `== executor_id` → rechazado — cubre tanto "no te apruebes a ti mismo"
  como "no apruebes lo que tú mismo vas a ejecutar", dos reglas
  distintas de la matriz.

## 7. Vista operativa / evidence links / handover (el resto del artefacto de este repo)

* **Vista operativa mínima**: `api/incidents.py`, `api/approvals.py`
  (listado/consulta) — probado en `tests/api/test_incidents_api.py`,
  `tests/api/test_approvals_api.py`.
* **Handover consumer/emulator**: `api/handover.py` — ciclo
  export→ack/retry, `SOC_MODE=SOC_EMULATED` explícito (sin endpoint SOC
  real todavía, ARG-022). Ver su propio docstring para el detalle
  completo.
* **Evidence links**: cada `Approval`/`ActionResult` referenciado por
  `run_id`/`action_id` es trazable hasta su `EvidenceManifest` vía
  `argos-validation/harness/evidence/manifest.py` y el panel operativo
  (`argos-validation/harness/reporters/evidence_panel.py`, ARG-026).

## Break-glass: fuera de alcance de este MVP, no un gap silenciado

`break-glass` aparece en la lista de ARG-028 para HITL/SOAR, pero el
propio documento maestro v0.6.25.4 define su versión formal en **Anexo
G.17 ("Break-glass formal y restringido")** con quality gate dedicado
(**ST-17: "Break-glass sin autoridad/TTL/scope/evidence" = 0**, tolerancia
cero) — y ese Anexo G, junto con el resto de Deep Assurance/Sovereign
Safety Kernel, está declarado explícitamente por el propio documento como
**"SPECIFIED / PREPARED - NOT EXECUTED"**, reservado a v0.6.26 ("v0.6.26
sigue reservada al cierre real"). Construir un break-glass parcial ahora
—sin doble control, TTL, scope y evidence exigidos por ST-17— sería peor
que no tenerlo: un control de seguridad a medias que aparenta existir.
No se implementa; se documenta aquí por qué, para que no se confunda con
un olvido.

Hoy, la única vía de excepción real es el **kill switch**
(`argos-platform/cyber-range/kill-switch/kill-switch.sh`) — que NO es
break-glass: corta egress y escala a cero, no otorga a nadie un permiso
de ejecución que de otro modo no tendría.
