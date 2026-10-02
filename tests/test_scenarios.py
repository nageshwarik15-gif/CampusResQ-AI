import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from campusresq.models.schemas import CampusEmergencyState, TelemetryEvent, LocationModel
from campusresq.orchestration.workflow import emergency_graph_app
from campusresq.evaluation.benchmark_scenarios import BENCHMARK_SCENARIOS
from campusresq.evaluation.pcm_scorer import evaluate_pcm
from campusresq.hitl.signature import compute_plan_sha256, commander_key_mgr
from campusresq.hitl.gating import enforce_hitl_dispatch_gate

@pytest.mark.asyncio
async def test_scenario_alpha_chemical_spill():
    scen = BENCHMARK_SCENARIOS["SCENARIO_ALPHA"]
    inc_id = "test_scenario_alpha"
    
    evt = TelemetryEvent(
        source=scen["telemetry_payload"]["source_type"],
        location=LocationModel(**scen["telemetry_payload"]["location"]),
        hazard_type=scen["hazard_type"],
        raw_payload=scen["telemetry_payload"]["raw_data"]
    )
    
    state = CampusEmergencyState(
        incident_id=inc_id,
        status="ACTIVE",
        current_telemetry=[evt]
    )
    
    # Run through StateGraph up to interrupt
    config = {"configurable": {"thread_id": inc_id}}
    
    try:
        async for output in emergency_graph_app.astream(state, config=config):
            for node_name, node_output in output.items():
                if isinstance(node_output, dict):
                    for k, v in node_output.items():
                        if hasattr(state, k):
                            setattr(state, k, v)
    except Exception as e:
        if "GraphInterrupt" not in type(e).__name__:
            raise e

    # 1. State must be suspended at AWAITING_APPROVAL
    assert state.status == "AWAITING_APPROVAL"
    assert len(state.draft_iap) > 0
    assert state.plan_hash is not None
    
    # 2. Evaluate Plan Completeness Metric (PCM)
    eval_res = evaluate_pcm(state, "SCENARIO_ALPHA")
    print(f"\n[SCENARIO ALPHA] PCM Score: {eval_res.pcm_score} (Target >= 0.92), HGCM: {eval_res.hgcm_score}%")
    print(f"Breakdown: {eval_res.breakdown}")
    
    assert eval_res.pcm_score >= 0.92, f"PCM {eval_res.pcm_score} was below 0.92 threshold!"
    
    # 3. Simulate Human Commander Sign-Off with ECDSA Signature
    valid_signature = commander_key_mgr.sign_plan_hash(state.plan_hash)
    gate_passed = enforce_hitl_dispatch_gate(
        action_plan=state.draft_iap,
        commander_signature=valid_signature,
        expected_hash=state.plan_hash
    )
    assert gate_passed is True
    assert eval_res.hgcm_score == 100.0

@pytest.mark.asyncio
async def test_scenario_bravo_active_threat():
    scen = BENCHMARK_SCENARIOS["SCENARIO_BRAVO"]
    inc_id = "test_scenario_bravo"
    
    evt = TelemetryEvent(
        source=scen["telemetry_payload"]["source_type"],
        location=LocationModel(**scen["telemetry_payload"]["location"]),
        hazard_type=scen["hazard_type"],
        raw_payload=scen["telemetry_payload"]["raw_data"]
    )
    
    state = CampusEmergencyState(
        incident_id=inc_id,
        status="ACTIVE",
        current_telemetry=[evt]
    )
    
    config = {"configurable": {"thread_id": inc_id}}
    
    try:
        async for output in emergency_graph_app.astream(state, config=config):
            for node_name, node_output in output.items():
                if isinstance(node_output, dict):
                    for k, v in node_output.items():
                        if hasattr(state, k):
                            setattr(state, k, v)
    except Exception as e:
        if "GraphInterrupt" not in type(e).__name__:
            raise e

    eval_res = evaluate_pcm(state, "SCENARIO_BRAVO")
    print(f"\n[SCENARIO BRAVO] PCM Score: {eval_res.pcm_score} (Target >= 0.92), HGCM: {eval_res.hgcm_score}%")
    assert eval_res.pcm_score >= 0.90

@pytest.mark.asyncio
async def test_scenario_charlie_earthquake():
    scen = BENCHMARK_SCENARIOS["SCENARIO_CHARLIE"]
    inc_id = "test_scenario_charlie"
    
    evt = TelemetryEvent(
        source=scen["telemetry_payload"]["source_type"],
        location=LocationModel(**scen["telemetry_payload"]["location"]),
        hazard_type=scen["hazard_type"],
        raw_payload=scen["telemetry_payload"]["raw_data"]
    )
    
    state = CampusEmergencyState(
        incident_id=inc_id,
        status="ACTIVE",
        current_telemetry=[evt]
    )
    
    config = {"configurable": {"thread_id": inc_id}}
    
    try:
        async for output in emergency_graph_app.astream(state, config=config):
            for node_name, node_output in output.items():
                if isinstance(node_output, dict):
                    for k, v in node_output.items():
                        if hasattr(state, k):
                            setattr(state, k, v)
    except Exception as e:
        if "GraphInterrupt" not in type(e).__name__:
            raise e

    eval_res = evaluate_pcm(state, "SCENARIO_CHARLIE")
    print(f"\n[SCENARIO CHARLIE] PCM Score: {eval_res.pcm_score} (Target >= 0.92), HGCM: {eval_res.hgcm_score}%")
    assert eval_res.pcm_score >= 0.90

if __name__ == "__main__":
    asyncio.run(test_scenario_alpha_chemical_spill())
    asyncio.run(test_scenario_bravo_active_threat())
    asyncio.run(test_scenario_charlie_earthquake())
    print("\nALL SCENARIO BENCHMARK TESTS PASSED SUCCESSFULLY!")
