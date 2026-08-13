# Changelog — argos-smartops

Formato basado en [Keep a Changelog](https://keepachangelog.com/), SemVer. Actualizar al finalizar cada sprint.

## [Unreleased]

### Added
- API FastAPI real (`incidents`, `recommendations`, `approvals`, `actions`, `evidence`, `handover`), UI server-rendered Jinja2 (cola, detalle, aprobación), modelos Pydantic validados contra `argos-contracts-scenarios`, autorización por rol y auditoría inmutable.
