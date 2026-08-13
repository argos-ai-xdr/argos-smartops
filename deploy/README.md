# deploy/

Un chart Helm real (`helm/argos-smartops/`), mismo patrón que `argos-core/deploy/helm/normalizer/`: falla en `helm template` sin `image.digest` fijado (ADR-013), namespace `argos-smartops` (`argos-platform/kubernetes/namespaces/argos-smartops.yaml`), `securityContext` compatible con Pod Security `restricted`.

`kustomize/` no tiene overlays propios — los namespaces/RBAC/NetworkPolicy base ya viven en `argos-platform`.
