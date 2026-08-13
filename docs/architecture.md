# Arquitectura de argos-smartops

Implementa el plano P5 (Operación) de `argos-control/architecture/logical/planos.md`: "Presentar contexto inmutable, aprobar/rechazar, monitorizar y exportar handover filtrado."

## Flujo

```
argos-core (Incident, Recommendation) ──▶ api/incidents, api/recommendations ──▶ web/ (cola, detalle)
                                                                                        │
                                                                          operador humano revisa
                                                                                        │
                                                                          web/ ──▶ api/approvals
                                                                                        │
                                                                          Approval (motivo, plan_hash, TTL)
                                                                                        │
                                                                          argos-cyber-tools/mcp_gateway
                                                                          (valida de forma INDEPENDIENTE)
                                                                                        │
                                                                          ActionResult ──▶ api/actions
                                                                                        │
                                                                          api/handover ──▶ SOC (ACK/reintento)
```

SmartOps **nunca** es la autoridad final de una acción: emite la `Approval`, pero `argos-cyber-tools/policies/approval` la revalida de cero (TTL, anti-replay, segregación, `plan_hash`) antes de que se ejecute nada. Si SmartOps estuviera comprometido, la peor consecuencia posible es una `Approval` que el gateway rechaza — no una ejecución no autorizada.

## Reglas que no se pueden romper

* `api/incidents` distingue explícitamente hechos (eventos, timeline) de inferencias (técnicas ATT&CK, confidence) en la respuesta — nunca los mezcla en un único campo de texto libre.
* `api/approvals` exige motivo, rol autorizado y `approver_id` distinto del `subject` que solicitó la acción — antes de emitir la `Approval`, no solo confía en la revalidación de `argos-cyber-tools`.
* `api/handover` no reimplementa la redacción TLP de `argos-core/services/soc_adapter` — solo gestiona el ciclo de vida del envío (ACK, reintento, historial).
* La UI nunca llama a un ejecutor directamente.

Ver `argos-control/architecture/data-flows/end-to-end-flow.md` para el flujo completo.
