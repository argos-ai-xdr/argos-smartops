# Desarrollo en argos-smartops

## Requisitos

* Python >= 3.11.
* `argos-contracts-scenarios` clonado como hermano de este repositorio (o `ARGOS_CONTRACTS_PATH`):

```text
argos-ai-xdr/
├── argos-smartops/          (este repositorio)
└── argos-contracts-scenarios/
```

## Comandos

```bash
make bootstrap   # pip install -e ".[dev]" + pre-commit install
make validate    # ruff + mypy + YAML/JSON
make test        # pytest (unit/api/e2e/authorization/accessibility)
make run         # levanta la app FastAPI local con recarga automática
```

## Datos de desarrollo

No hay clientes reales todavía hacia `argos-core`/`argos-cyber-tools` (ARG-022 los conectará). `api/` usa un repositorio en memoria (`InMemoryIncidentRepository`, etc.) sembrado con los fixtures `smoke/` de `argos-contracts-scenarios` — mismo patrón que `argos-validation`/`argos-core`, para poder desarrollar y probar sin desplegar el resto del sistema.

## Antes de abrir un PR

1. `make validate` y `make test` sin errores, incluidos `tests/authorization/` y `tests/accessibility/`.
2. El PR enlaza una historia `ARG-###`.
3. Ninguna vista mezcla hechos e inferencias sin distinguirlas.
