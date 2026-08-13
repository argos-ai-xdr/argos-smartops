# web/

UI server-rendered (Jinja2). Monta en la raíz (`/incidents`, no `/api/incidents`) — la API JSON vive bajo `/api` (ver `api/app.py`, donde se documenta el bug real de colisión de rutas que forzó esa separación).

| Módulo | Contenido |
| --- | --- |
| [`routes.py`](routes.py) | Cola, detalle (hechos/inferencias separados en el HTML), formulario de aprobación — reutiliza `api.approvals.create_approval` como función Python directa, no vía HTTP |
| [`templates/`](templates/) | `base.html`, `incidents_queue.html`, `incident_detail.html`, `approval_form.html` |
| [`audit.py`](audit.py) | `AuditLog` real e inmutable — sin método de borrado/modificación |

## Nota de estructura

El árbol de bootstrap original ponía `auth/` y `audit/` como subcarpetas de `web/`. `audit.py` sí vive aquí (solo lo usa la UI). El núcleo de autorización (`Operator`, `require_role`) se movió a `api/auth.py` porque `api/approvals.py` lo necesita directamente y `web/` ya depende de `api/` — ponerlo bajo `web/` habría invertido esa dependencia sin necesidad. `web/` importa `api.auth`, no al revés.
