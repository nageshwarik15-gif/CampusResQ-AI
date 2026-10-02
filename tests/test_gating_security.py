import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from campusresq.hitl.signature import canonical_json, compute_plan_sha256, commander_key_mgr, SecurityGatingError
from campusresq.hitl.gating import enforce_hitl_dispatch_gate, gating_tracker
from campusresq.models.schemas import TacticalAction

def test_canonical_json_determinism():
    """Verify Canonical JSON outputs deterministic identical strings regardless of dict key insertion order."""
    dict1 = {"b": 2, "a": 1, "c": [3, 4]}
    dict2 = {"a": 1, "c": [3, 4], "b": 2}
    assert canonical_json(dict1) == canonical_json(dict2)
    assert canonical_json(dict1) == '{"a":1,"b":2,"c":[3,4]}'

def test_tamper_evident_plan_hash():
    """Modifying even one character of a tactical instruction alters the SHA-256 fingerprint."""
    action1 = TacticalAction(
        action_id="ACT_001",
        tier="TIER_A_CRITICAL",
        priority="P1_IMMEDIATE",
        category="EVACUATION",
        target="West Stairwell",
        instruction="Evacuate via West Stairwell",
        rationale="Safe egress"
    )
    hash1 = compute_plan_sha256([action1])
    
    # Slight tamper
    action2 = TacticalAction(
        action_id="ACT_001",
        tier="TIER_A_CRITICAL",
        priority="P1_IMMEDIATE",
        category="EVACUATION",
        target="West Stairwell",
        instruction="Evacuate via East Stairwell",  # TAMPERED
        rationale="Safe egress"
    )
    hash2 = compute_plan_sha256([action2])
    
    assert hash1 != hash2

def test_hgcm_compliance():
    """Verify HGCM tracking maintains zero tolerance."""
    gating_tracker.total_attempted_tier_a = 10
    gating_tracker.properly_gated_tier_a = 10
    assert gating_tracker.compute_hgcm() == 100.0

if __name__ == "__main__":
    test_canonical_json_determinism()
    test_tamper_evident_plan_hash()
    test_hgcm_compliance()
    print("ALL GATING & SECURITY TESTS PASSED!")
