# Contribuir a argos-smartops

1. Toda historia debe existir como issue `ARG-###` (ver `argos-control/project/backlog/backlog.yaml`). Primeras historias: contrato del approval API, wireframe de incidente, vista mínima de recomendación, aprobación/rechazo, ARG-022 (SmartOps y SOC handover).
2. Rama de trabajo: `feat/ARG-###-descripcion-corta`, `fix/...`.
3. Pull request obligatorio contra `main`. Sin push directo, force-push ni borrado de `main`.
4. Ninguna vista de incidente puede mezclar hechos (eventos, timeline) con inferencias (técnicas ATT&CK, confidence) sin distinguirlas visualmente — es un requisito P0, no un detalle de estilo.
5. `api/approvals/` no acepta una aprobación sin motivo, sin `approver_id` distinto del solicitante, ni sin `plan_hash` visible para el operador antes de confirmar.
6. La UI nunca almacena secretos (tokens OIDC, credenciales) en sesión persistida más allá de lo que exige la propia biblioteca de sesión — ver `web/auth/`.
7. `make validate` y `make test` deben pasar, incluidos `tests/authorization/` y `tests/accessibility/`.
