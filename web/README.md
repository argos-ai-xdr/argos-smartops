# web/

UI server-rendered (Jinja2). Monta en la raíz (`/incidents`, no `/api/incidents`) — la API JSON vive bajo `/api` (ver `api/app.py`, donde se documenta el bug real de colisión de rutas que forzó esa separación).

| Módulo | Contenido |
| --- | --- |
| [`routes.py`](routes.py) | Cola, detalle (hechos/inferencias separados en el HTML), formulario de aprobación — reutiliza `api.approvals.create_approval` como función Python directa, no vía HTTP |
| [`templates/`](templates/) | `base.html`, `incidents_queue.html`, `incident_detail.html`, `approval_form.html` |

## Nota de estructura

El árbol de bootstrap original ponía `auth/` y `audit/` como subcarpetas de `web/`. Los dos terminaron en `api/`: el núcleo de autorización (`Operator`, `require_role`) se movió a `api/auth.py` porque `api/approvals.py` lo necesita directamente, y `AuditLog`/`get_audit_log` a `api/audit.py` por la misma razón en cuanto `api/handover.py` empezó a auditar sus propias transiciones — en ambos casos, ponerlo bajo `web/` habría invertido la dependencia (`web/` ya depende de `api/`, no al revés). `web/routes.py` importa `api.auth` y `api.audit`, no al revés.
