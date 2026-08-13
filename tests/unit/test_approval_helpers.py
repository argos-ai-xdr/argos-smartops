from __future__ import annotations

from api.approvals import compute_plan_hash, compute_signature_ref


def test_plan_hash_is_deterministic():
    a = compute_plan_hash(action_id="pol-1", decision="APPROVE")
    b = compute_plan_hash(action_id="pol-1", decision="APPROVE")
    assert a == b


def test_plan_hash_differs_for_different_action_or_decision():
    a = compute_plan_hash(action_id="pol-1", decision="APPROVE")
    b = compute_plan_hash(action_id="pol-2", decision="APPROVE")
    c = compute_plan_hash(action_id="pol-1", decision="REJECT")
    assert len({a, b, c}) == 3


def test_signature_ref_depends_on_both_approval_id_and_plan_hash():
    plan_hash = compute_plan_hash(action_id="pol-1", decision="APPROVE")
    sig_a = compute_signature_ref("appr-1", plan_hash)
    sig_b = compute_signature_ref("appr-2", plan_hash)
    assert sig_a != sig_b
