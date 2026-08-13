# Política de seguridad — argos-smartops

Ver la política transversal en `argos-control/SECURITY.md`. Específico de este repositorio:

* La UI nunca llama directamente a un `executor` de `argos-cyber-tools`: solo emite `Approval` a través de `api/approvals/`, que `argos-cyber-tools/policies/approval` valida de forma independiente (TTL, anti-replay, segregación, `plan_hash`) antes de que nada se ejecute. SmartOps no es el control de seguridad — es donde se genera la decisión humana que ese control exige.
* `Approval.approver_id` nunca puede coincidir con el `subject` que solicitó la acción (mismo requisito que `argos-cyber-tools/policies/approval`); `api/approvals/` lo rechaza en el momento de crear la aprobación, no solo se confía en que `argos-cyber-tools` lo valide después.
* El handover SOC (`api/handover/`) filtra por TLP antes de exportar — la lógica de redacción vive en `argos-core/services/soc_adapter`; SmartOps no debe reimplementarla ni relajarla.
* Ningún secreto (token OIDC, credencial de servicio) se almacena en el DOM ni en cookies no `httponly`/no `secure`.

## Reporte

Reportar vulnerabilidades o hallazgos vía el issue template `risk.yaml` o `exception.yaml` de `argos-control`, notificando al rol `qa-security-observer`.
