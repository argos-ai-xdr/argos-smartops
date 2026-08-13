"""Chequeos de accesibilidad reales sobre el HTML ya renderizado — no una
herramienta externa (axe-core, etc., no disponible en este bootstrap), pero
sí verificaciones estructurales concretas y automatizables.
"""
from __future__ import annotations

import re


def test_pages_declare_spanish_language(approver_client):
    for path in ["/incidents", "/incidents/incident-smoke-001", "/incidents/incident-smoke-001/approve"]:
        r = approver_client.get(path)
        assert '<html lang="es">' in r.text, f"{path} no declara lang"


def test_queue_table_has_column_headers_with_scope(approver_client):
    r = approver_client.get("/incidents")
    assert re.search(r'<th scope="col">', r.text), "la tabla de la cola debe usar <th scope=\"col\">"
    assert "<caption>" in r.text, "la tabla debe tener <caption> para lectores de pantalla"


def test_approval_form_inputs_have_associated_labels(approver_client):
    r = approver_client.get("/incidents/incident-smoke-001/approve")
    html = r.text
    for field_id in ["decision-approve", "decision-reject", "reason", "target-confirmed"]:
        assert f'for="{field_id}"' in html, f"falta <label for=\"{field_id}\">"
        assert f'id="{field_id}"' in html, f"falta el input con id=\"{field_id}\""


def test_approval_form_required_fields_are_marked_required(approver_client):
    r = approver_client.get("/incidents/incident-smoke-001/approve")
    html = r.text
    assert 'name="reason" required' in html
    assert 'name="target_confirmed" value="true" required' in html


def test_incident_detail_uses_heading_hierarchy_not_just_bold_text(approver_client):
    r = approver_client.get("/incidents/incident-smoke-001")
    html = r.text
    assert "<h1>" in html
    assert '<h2 id="facts-heading">' in html
    assert '<h2 id="inferences-heading">' in html
    # Las secciones facts/inferences deben ser <section> identificables, no divs genéricos.
    assert 'aria-labelledby="facts-heading"' in html
    assert 'aria-labelledby="inferences-heading"' in html


def test_pages_have_a_title(approver_client):
    for path in ["/incidents", "/incidents/incident-smoke-001"]:
        r = approver_client.get(path)
        assert re.search(r"<title>[^<]+</title>", r.text), f"{path} no tiene <title>"
