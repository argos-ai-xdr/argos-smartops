# generated_contracts/

Modelos Pydantic (`IncidentOut`, `RecommendationOut`, `ApprovalCreate`/`ApprovalOut`, `ActionResultOut`, `EvidenceManifestOut`, `SOCHandoverOut`) para tipado y OpenAPI — más `validate_payload`, que valida contra el JSON Schema real de `argos-contracts-scenarios/schemas/`. Pydantic solo no basta: no conoce las reglas cruzadas (`allOf`, `anyOf`) de los schemas reales, así que toda respuesta de `api/` pasa por ambos.

`ApprovalCreate` no acepta `approver_id` en el body — lo asigna el servidor desde la sesión autenticada (`web/auth/`) para que un cliente no pueda autoasignarse aprobador de su propia solicitud.
