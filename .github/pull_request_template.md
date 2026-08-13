## Historia

Enlaza la historia `ARG-###` (obligatorio): closes ARG-

## Qué cambia y por qué

## Checklist

- [ ] `make validate` y `make test` pasan localmente, incluidos `tests/authorization/` y `tests/accessibility/`.
- [ ] Ninguna vista de incidente mezcla hechos e inferencias sin distinguirlas.
- [ ] `api/approvals` sigue exigiendo motivo, rol y `approver_id` != `subject`.
- [ ] La UI no llama directamente a un ejecutor ni almacena secretos.

## Evidencia / cómo se validó
