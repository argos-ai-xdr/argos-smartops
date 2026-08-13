from __future__ import annotations

from api.approvals import compute_plan_hash, compute_signature_ref


def test_plan_hash_is_deterministic():
    a = compute_plan_hash(tool="isolate_kubernetes_workload", target="deployment/gseg-simulado", action="execute")
    b = compute_plan_hash(tool="isolate_kubernetes_workload", target="deployment/gseg-simulado", action="execute")
    assert a == b


def test_plan_hash_differs_for_different_tool_target_or_action():
    a = compute_plan_hash(tool="isolate_kubernetes_workload", target="deployment/gseg-simulado", action="execute")
    b = compute_plan_hash(tool="scale_to_zero", target="deployment/gseg-simulado", action="execute")
    c = compute_plan_hash(tool="isolate_kubernetes_workload", target="deployment/otro", action="execute")
    d = compute_plan_hash(tool="isolate_kubernetes_workload", target="deployment/gseg-simulado", action="dry-run")
    assert len({a, b, c, d}) == 4


def test_signature_ref_depends_on_both_approval_id_and_plan_hash():
    plan_hash = compute_plan_hash(tool="isolate_kubernetes_workload", target="deployment/gseg-simulado", action="execute")
    sig_a = compute_signature_ref("appr-1", plan_hash)
    sig_b = compute_signature_ref("appr-2", plan_hash)
    assert sig_a != sig_b
