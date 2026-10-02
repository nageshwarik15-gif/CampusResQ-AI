import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import pytest
except ImportError:
    pytest = None

import networkx as nx
from campusresq.spatial.campus_graph import build_campus_building_graph, HazardZone
from campusresq.spatial.routing import compute_evacuation_routes
from campusresq.orchestration.arbitration import arbitrate_and_prioritize
from campusresq.models.schemas import TacticalAction, CampusEmergencyState, TelemetryEvent, LocationModel
from campusresq.hitl.signature import compute_plan_sha256, commander_key_mgr, SecurityGatingError
from campusresq.hitl.gating import enforce_hitl_dispatch_gate, gating_tracker
from campusresq.evaluation.pcm_scorer import evaluate_pcm

def test_algorithm_1_evacuation_pathing():
    """Verify Algorithm 1: Egress paths avoid active hazard and prioritize safe exits."""
    graph = build_campus_building_graph("CHEM_HALL")
    
    # Epicenter at Room 302 (25.0, 30.0) with lethal radius 12m and danger radius 30m
    hazards = [
        HazardZone("HAZ_CHEM", "Toxic Solvent Spill", (25.0, 30.0), lethal_radius=12.0, danger_radius=30.0)
    ]
    
    result = compute_evacuation_routes(graph, hazards, graph.safe_exits)
    assert "routes" in result
    routes = result["routes"]
    
    # Room 301 is to the west, should evacuate via West Stairwell
    assert "ROOM_301" in routes
    path_301 = routes["ROOM_301"]
    assert "STAIRWELL_WEST_3" in path_301
    assert "EXIT_WEST_GROUND" in path_301
    # Must NOT route through Room 302 epicenter
    assert "ROOM_302" not in path_301

def test_algorithm_2_arbitration_and_priority_sorting():
    """Verify Algorithm 2: Filters hard violations and sorts by ICS Life-Safety priority."""
    actions = [
        TacticalAction(
            action_id="ACT_LOW",
            tier="TIER_C_INFORMATIONAL",
            priority="P4_LOW",
            category="PUBLIC_ALERT",
            target="Website",
            instruction="Post website update",
            rationale="Informational"
        ),
        TacticalAction(
            action_id="ACT_CRIT_EVAC",
            tier="TIER_A_CRITICAL",
            priority="P1_IMMEDIATE",
            category="EVACUATION",
            target="Floor 3",
            instruction="Evacuate Floor 3",
            rationale="Life safety"
        ),
        TacticalAction(
            action_id="ACT_VIOLATION",
            tier="TIER_A_CRITICAL",
            priority="P1_IMMEDIATE",
            category="EVACUATION",
            target="Elevators",
            instruction="Use elevators",
            rationale="SOP violation"
        ),
        TacticalAction(
            action_id="ACT_RES",
            tier="TIER_B_OPERATIONAL",
            priority="P2_HIGH",
            category="MEDICAL",
            target="Lot 4",
            instruction="Stage ambulances",
            rationale="Medical care"
        )
    ]
    
    hard_violations = {"ACT_VIOLATION"}
    safe_sorted = arbitrate_and_prioritize(actions, hard_violations)
    
    # 1. Violation must be removed
    assert not any(a.action_id == "ACT_VIOLATION" for a in safe_sorted)
    
    # 2. Priority 1 must be first
    assert safe_sorted[0].action_id == "ACT_CRIT_EVAC"
    assert safe_sorted[0].priority == "P1_IMMEDIATE"
    
    # 3. Priority 2 next
    assert safe_sorted[1].action_id == "ACT_RES"
    
    # 4. Priority 4 last
    assert safe_sorted[-1].action_id == "ACT_LOW"

def test_algorithm_4_deterministic_gating():
    """Verify Algorithm 4: Tier-A actions NEVER execute without valid cryptographic signature."""
    critical_action = TacticalAction(
        action_id="ACT_TIER_A",
        tier="TIER_A_CRITICAL",
        priority="P1_IMMEDIATE",
        category="EVACUATION",
        target="Chemistry Hall",
        instruction="Order mandatory campus evacuation",
        rationale="Life safety"
    )
    
    plan = [critical_action]
    plan_hash = compute_plan_sha256(plan)
    
    # Attempt 1: Without signature -> MUST RAISE SecurityGatingError
    with pytest.raises(SecurityGatingError) as exc_info:
        enforce_hitl_dispatch_gate(plan, commander_signature=None, expected_hash=plan_hash)
    assert "without human signature" in str(exc_info.value)
    
    # Attempt 2: With invalid / forged signature -> MUST RAISE SecurityGatingError
    with pytest.raises(SecurityGatingError) as exc_info:
        enforce_hitl_dispatch_gate(plan, commander_signature="FORGED_INVALID_SIGNATURE==", expected_hash=plan_hash)
    assert "Invalid cryptographic signature" in str(exc_info.value)
    
    # Attempt 3: With valid ECDSA signature -> MUST PASS
    valid_sig = commander_key_mgr.sign_plan_hash(plan_hash)
    success = enforce_hitl_dispatch_gate(plan, commander_signature=valid_sig, expected_hash=plan_hash)
    assert success is True

if __name__ == "__main__":
    test_algorithm_1_evacuation_pathing()
    test_algorithm_2_arbitration_and_priority_sorting()
    test_algorithm_4_deterministic_gating()
    print("ALL CORE ALGORITHM UNIT TESTS PASSED!")
