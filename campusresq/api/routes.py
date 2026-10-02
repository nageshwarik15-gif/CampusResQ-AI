"""
RESTful API Endpoints
Conforms strictly to IEEE 1016-2009 SDD §7.1 and SRS §4.4.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from typing import Dict, Any, List, Optional
import uuid
import asyncio
from datetime import datetime, timezone

from ..models.schemas import (
    IncidentTelemetryPayload,
    CampusEmergencyState,
    TelemetryEvent,
    ApprovalRequest,
    HumanApprovalRecord,
    EvaluationResult,
    TacticalAction,
    current_iso_time
)
from ..orchestration.workflow import emergency_graph_app
from ..orchestration.replan import execute_replan_node
from ..orchestration.arbitration import arbitrate_and_prioritize
from ..hitl.signature import commander_key_mgr, compute_plan_sha256, SecurityGatingError
from ..hitl.gating import enforce_hitl_dispatch_gate
from ..dispatch.actuator_manager import actuator_mgr
from ..evaluation.benchmark_scenarios import BENCHMARK_SCENARIOS
from ..evaluation.pcm_scorer import evaluate_pcm
from ..storage.db import db
from .websocket_broker import ws_broker
from ..security.sanitizer import sanitize_telemetry_payload, sanitize_text

router = APIRouter(prefix="/api/v1", tags=["Campus Emergency Coordinator"])

# Background execution runner for LangGraph workflow
async def run_incident_graph(state: CampusEmergencyState):
    db.save_incident_state(state)
    
    # Execute graph up to interrupt_before=["dispatch_execution_node"]
    config = {"configurable": {"thread_id": state.incident_id}}
    
    try:
        async for output in emergency_graph_app.astream(state, config=config):
            for node_name, node_output in output.items():
                if isinstance(node_output, dict):
                    for k, v in node_output.items():
                        if hasattr(state, k):
                            setattr(state, k, v)
            db.save_incident_state(state)
    except Exception as e:
        if "GraphInterrupt" not in type(e).__name__:
            raise e
        db.save_incident_state(state)

@router.post("/incidents/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_emergency_event(payload: IncidentTelemetryPayload, background_tasks: BackgroundTasks):
    """
    Ingest Emergency Event (SDD §7.1.1)
    Receives simulated telemetry or manual dispatch alert.
    Response: 202 Accepted -> {"incident_id": "...", "status": "PROCESSING", "run_id": "..."}
    """
    # Sanitize input telemetry against prompt injection and malicious instructions (SDD §9.1)
    payload = sanitize_telemetry_payload(payload)

    telemetry_evt = TelemetryEvent(
        source=payload.source_type,
        location=payload.location,
        hazard_type=payload.raw_data.get("hazard_indicators", ["GENERAL_HAZARD"])[0] if payload.raw_data.get("hazard_indicators") else "GENERAL_HAZARD",
        raw_payload=payload.raw_data
    )
    
    incident_state = CampusEmergencyState(
        incident_id=payload.incident_id,
        status="PROCESSING",
        current_telemetry=[telemetry_evt]
    )
    
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    db.save_incident_state(incident_state)
    
    # Launch cognitive graph asynchronously
    background_tasks.add_task(run_incident_graph, incident_state)
    
    return {
        "incident_id": payload.incident_id,
        "status": "PROCESSING",
        "run_id": run_id,
        "timestamp": current_iso_time()
    }

@router.get("/incidents/{incident_id}/state", response_model=CampusEmergencyState)
async def get_incident_current_state(incident_id: str):
    """
    Get Incident Current State (SDD §7.1.2)
    Returns full blackboard state, including draft IAP and sub-agent analysis.
    """
    state = db.get_incident_state(incident_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    return state

@router.post("/incidents/{incident_id}/approve")
async def submit_human_approval_and_override(incident_id: str, request: ApprovalRequest):
    """
    Submit Human Approval & Override (SDD §7.1.3)
    Submits commander's decision and cryptographic signature to resume the LangGraph workflow.
    """
    state = db.get_incident_state(incident_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
        
    now = current_iso_time()
    
    # Check if this is a request for replanning with feedback (SDD §5.2)
    if request.decision == "REJECTED_REDRAFT_REQUESTED" or request.feedback_text:
        feedback = request.feedback_text or "Commander requested redraft."
        updated_state = await execute_replan_node(state, feedback, request.action_overrides)
        db.save_incident_state(updated_state)
        
        await ws_broker.broadcast_event(
            incident_id,
            "AGENT_THOUGHT",
            {"agent": "Orchestrator", "text": f"ReplanNode executed with feedback: '{feedback}'. Refreshed plan diff compiled."}
        )
        await ws_broker.broadcast_event(
            incident_id,
            "IAP_DRAFT_READY",
            {"plan_hash": updated_state.plan_hash, "status": "AWAITING_APPROVAL", "diff_available": True}
        )
        return {
            "status": "REPLANNED",
            "message": "Sub-plans re-synthesized with human guidance.",
            "plan_hash": updated_state.plan_hash,
            "iteration_count": updated_state.iteration_count
        }

    # Handle line-item overrides (APPROVED_WITH_MODIFICATIONS)
    approved_actions = []
    override_map = {o.action_id: o for o in request.action_overrides}
    
    for act in state.draft_iap:
        if act.action_id in override_map:
            ov = override_map[act.action_id]
            if ov.override_status == "DELETED":
                continue
            elif ov.override_status == "MODIFIED":
                if ov.modified_instruction:
                    act.instruction = ov.modified_instruction
                act.status = "APPROVED"
                act.override_notes = ov.human_override_notes or "Commander modified"
                approved_actions.append(act)
            elif ov.override_status == "ACCEPTED":
                act.status = "APPROVED"
                approved_actions.append(act)
        else:
            act.status = "APPROVED"
            approved_actions.append(act)
            
    state.approved_iap = approved_actions
    state.approval_signature = request.digital_signature
    state.status = "DISPATCHED"
    
    # Algorithm 4: Deterministic Gating Enforcement
    try:
        enforce_hitl_dispatch_gate(
            action_plan=approved_actions,
            commander_signature=request.digital_signature,
            expected_hash=state.plan_hash
        )
    except SecurityGatingError as err:
        raise HTTPException(status_code=403, detail=str(err))

    # Dispatch to actuators
    dispatch_logs = actuator_mgr.dispatch_approved_plan(approved_actions, incident_id)
    db.record_dispatch_logs(dispatch_logs)
    
    # Save human approval record
    approval_rec = HumanApprovalRecord(
        plan_id=request.plan_id,
        commander_id=request.commander_id,
        timestamp=now,
        decision=request.decision,
        modifications=[o.model_dump() for o in request.action_overrides],
        digital_signature=request.digital_signature or ""
    )
    db.record_approval(approval_rec)
    db.save_incident_state(state)
    
    await ws_broker.broadcast_event(
        incident_id,
        "AGENT_THOUGHT",
        {"agent": "HITL_Gate", "text": f"Cryptographic signature verified. Dispatched {len(dispatch_logs)} emergency orders."}
    )
    
    return {
        "status": "DISPATCHING",
        "approved_count": len(approved_actions),
        "dispatched_at": now,
        "dispatch_receipts": [l.model_dump() for l in dispatch_logs]
    }

@router.get("/incidents/{incident_id}/evaluate", response_model=EvaluationResult)
async def evaluate_incident_benchmarks(incident_id: str, scenario_id: str = "SCENARIO_ALPHA"):
    """
    Post-Incident Benchmark Evaluation (SDD §7.1.4)
    Calculates and returns the Plan Completeness Metric (PCM) and Human-Gating Correctness Metric (HGCM).
    """
    state = db.get_incident_state(incident_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
        
    eval_res = evaluate_pcm(state, scenario_id)
    return eval_res

@router.post("/incidents/simulate/{scenario_id}")
async def trigger_simulated_scenario(scenario_id: str, background_tasks: BackgroundTasks):
    """
    Triggers one of the standard benchmark scenarios: SCENARIO_ALPHA, SCENARIO_BRAVO, SCENARIO_CHARLIE (SRS §7.4).
    """
    scenario_key = scenario_id.upper()
    if scenario_key not in BENCHMARK_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario_id}'. Valid: {list(BENCHMARK_SCENARIOS.keys())}")
        
    scen = BENCHMARK_SCENARIOS[scenario_key]
    inc_id = f"inc_{scenario_key.lower()}_{uuid.uuid4().hex[:6]}"
    
    payload = IncidentTelemetryPayload(
        incident_id=inc_id,
        source_type=scen["telemetry_payload"]["source_type"],
        location=scen["telemetry_payload"]["location"],
        raw_data=scen["telemetry_payload"]["raw_data"]
    )
    
    res = await ingest_emergency_event(payload, background_tasks)
    res["scenario_name"] = scen["name"]
    res["description"] = scen["description"]
    return res

@router.post("/incidents/{incident_id}/inject")
async def inject_dynamic_disruption(incident_id: str, inject_payload: Dict[str, Any]):
    """
    Live Event Injection (FR-1.3):
    e.g., 'Fire spreads to Stairwell B at T+4 minutes'.
    Triggers dynamic plan reassessment and replan loop.
    """
    state = db.get_incident_state(incident_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
        
    note = inject_payload.get("note", "Environmental condition updated.")
    note = sanitize_text(note)
    new_evt = TelemetryEvent(
        source="environmental_inject",
        location=state.current_telemetry[-1].location if state.current_telemetry else None,
        hazard_type="SECONDARY_HAZARD_SPREAD",
        raw_payload=inject_payload
    )
    state.current_telemetry.append(new_evt)
    
    # Execute replan with this environmental inject
    updated_state = await execute_replan_node(state, f"INJECT: {note}")
    db.save_incident_state(updated_state)
    
    await ws_broker.broadcast_event(
        incident_id,
        "AGENT_THOUGHT",
        {"agent": "SimulationInjector", "text": f"Dynamic inject applied: '{note}'. Triggering plan reassessment."}
    )
    
    return {
        "status": "INJECT_PROCESSED",
        "incident_id": incident_id,
        "plan_hash": updated_state.plan_hash
    }

@router.get("/incidents")
async def list_all_incidents():
    """List all recent and active incidents."""
    return db.list_incidents()

@router.get("/audit/{incident_id}/export")
async def export_fema_audit_report(incident_id: str):
    """
    1-Click FEMA After-Action Audit Log Export (FR-7.2).
    """
    return db.export_after_action_report(incident_id)

@router.get("/commander/credentials")
async def get_commander_credentials():
    """
    Returns public key and signing helper utilities for Incident Commander UI.
    """
    return {
        "commander_id": "CHIEF_MILLER_01",
        "rank": "Campus Police Chief / Incident Commander",
        "public_key_pem": commander_key_mgr.public_pem,
        "algorithm": "ECDSA_SECP256R1_SHA256"
    }

@router.post("/commander/sign")
async def sign_plan_for_commander(payload: Dict[str, str]):
    """
    Convenience endpoint for UI: Signs the given plan_hash with Commander's private key.
    """
    plan_hash = payload.get("plan_hash")
    if not plan_hash:
        raise HTTPException(status_code=400, detail="Missing plan_hash")
    sig = commander_key_mgr.sign_plan_hash(plan_hash)
    return {
        "plan_hash": plan_hash,
        "digital_signature": sig,
        "commander_id": "CHIEF_MILLER_01"
    }
