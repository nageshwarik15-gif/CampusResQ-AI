"""
LangGraph Multi-Agent StateGraph Architecture
Conforms strictly to IEEE 1016-2009 SDD §3.1, §5.1 and SRS §3.1, §3.4.
Provides persistent state checkpointing, parallel specialist deliberation, and deterministic HITL gating.
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from ..models.schemas import CampusEmergencyState, TacticalAction
from ..rag.database import rag_db
from ..agents.triage_agent import TriageHazardAgent
from ..agents.evacuation_agent import EvacuationAgent
from ..agents.resource_agent import ResourceAllocationAgent
from ..agents.comms_agent import CrisisPublicCommunicationsAgent
from ..agents.safety_guardrail import SafetyGuardrailAgent
from ..agents.orchestrator import IncidentOrchestratorAgent
from ..hitl.signature import compute_plan_sha256, commander_key_mgr
from ..hitl.gating import enforce_hitl_dispatch_gate
from ..dispatch.actuator_manager import actuator_mgr
from ..events import event_bus as ws_broker

# Agent Instances
triage_agent = TriageHazardAgent()
evac_agent = EvacuationAgent()
resource_agent = ResourceAllocationAgent()
comms_agent = CrisisPublicCommunicationsAgent()
safety_guardrail = SafetyGuardrailAgent()
orchestrator = IncidentOrchestratorAgent()

def parse_state(state: Union[CampusEmergencyState, Dict[str, Any]]) -> CampusEmergencyState:
    if isinstance(state, CampusEmergencyState):
        return state
    return CampusEmergencyState(**state)

async def ingest_incident_node(state: CampusEmergencyState) -> Dict[str, Any]:
    current_state = parse_state(state)
    await ws_broker.broadcast_event(
        current_state.incident_id,
        "AGENT_THOUGHT",
        {"agent": "Orchestrator", "text": f"Incident {current_state.incident_id} ingested. Telemetry normalized."}
    )
    return {"status": "ACTIVE"}

async def rag_context_retrieval_node(state: CampusEmergencyState) -> Dict[str, Any]:
    current_state = parse_state(state)
    building_id = "CHEM_HALL"
    hazard_type = "HAZMAT"
    
    if current_state.current_telemetry:
        latest = current_state.current_telemetry[-1]
        building_id = latest.location.building_id
        hazard_type = latest.hazard_type
        
    query = f"Emergency operations protocol and safety data for {building_id} {hazard_type}"
    retrieved_chunks = rag_db.hybrid_search(
        query=query, 
        building_id=building_id, 
        hazard_type=hazard_type, 
        top_k=3
    )
    
    await ws_broker.broadcast_event(
        current_state.incident_id,
        "AGENT_THOUGHT",
        {
            "agent": "RAG_Core",
            "text": f"Retrieved {len(retrieved_chunks)} grounded SOP/SDS chunks. Top match: {retrieved_chunks[0]['title']} (RRF: {retrieved_chunks[0]['rrf_score']})"
        }
    )
    
    return {"rag_context": retrieved_chunks}

async def parallel_specialist_deliberation_node(state: CampusEmergencyState) -> Dict[str, Any]:
    current_state = parse_state(state)
    incident_id = current_state.incident_id
    
    # 1. Run Triage Agent
    triage_result = await triage_agent.run(current_state)
    current_state.triage_assessment = triage_result
    
    await ws_broker.broadcast_event(
        incident_id,
        "SUBPLAN_GENERATED",
        {"agent": "TriageAgent", "data": triage_result["assessment"]}
    )
    
    # 2. Parallel execution of Evacuation & Resource allocation (FR-3.1)
    evac_task = asyncio.create_task(evac_agent.run(current_state))
    resource_task = asyncio.create_task(resource_agent.run(current_state))
    
    evac_result, resource_result = await asyncio.gather(evac_task, resource_task)
    
    await ws_broker.broadcast_event(
        incident_id,
        "SUBPLAN_GENERATED",
        {"agent": "EvacuationAgent", "routes_count": len(evac_result.get("routes", {}))}
    )
    await ws_broker.broadcast_event(
        incident_id,
        "SUBPLAN_GENERATED",
        {"agent": "ResourceAgent", "units_assigned": len(resource_result.get("units_dispatched", []))}
    )
    
    # Broadcast map vector updates
    if "routes" in evac_result:
        await ws_broker.broadcast_event(
            incident_id,
            "MAP_VECTOR_UPDATE",
            {
                "hazard_center": [37.4278, -122.1695],
                "containment_radius": (triage_result.get("assessment", {})).get("containment_radius_meters", 150.0),
                "safe_routes": evac_result["routes"]
            }
        )
        
    return {
        "triage_assessment": triage_result,
        "evacuation_routes": evac_result,
        "resource_assignments": resource_result
    }

async def crisis_comms_node(state: CampusEmergencyState) -> Dict[str, Any]:
    current_state = parse_state(state)
    comms_result = await comms_agent.run(current_state)
    
    await ws_broker.broadcast_event(
        current_state.incident_id,
        "SUBPLAN_GENERATED",
        {"agent": "CrisisCommsAgent", "sms": comms_result.get("sms_broadcast")}
    )
    return {"crisis_communications": comms_result}

async def safety_guardrail_node(state: CampusEmergencyState) -> Dict[str, Any]:
    current_state = parse_state(state)
    audit_result = await safety_guardrail.run(current_state)
    
    await ws_broker.broadcast_event(
        current_state.incident_id,
        "AGENT_THOUGHT",
        {
            "agent": "SafetyGuardrail",
            "text": f"Audit complete. Safety Confidence Score: {audit_result['safety_confidence_score']}%. Violations: {len(audit_result['hard_violations'])}"
        }
    )
    return {"safety_audit_report": audit_result}

async def plan_arbitration_node(state: CampusEmergencyState) -> Dict[str, Any]:
    current_state = parse_state(state)
    orch_result = await orchestrator.run(current_state)
    draft_iap = orch_result.get("draft_iap", [])
    
    # Compute deterministic SHA-256 fingerprint (SDD §5.3)
    plan_hash = compute_plan_sha256(draft_iap)
    
    await ws_broker.broadcast_event(
        current_state.incident_id,
        "IAP_DRAFT_READY",
        {
            "plan_hash": plan_hash,
            "actions_count": len(draft_iap),
            "status": "AWAITING_APPROVAL"
        }
    )
    
    return {
        "draft_iap": [a if isinstance(a, TacticalAction) else TacticalAction(**a) for a in draft_iap],
        "status": "AWAITING_APPROVAL",
        "plan_hash": plan_hash
    }

async def dispatch_execution_node(state: CampusEmergencyState) -> Dict[str, Any]:
    current_state = parse_state(state)
    
    approved_actions = [
        TacticalAction(**a) if isinstance(a, dict) else a 
        for a in current_state.approved_iap or current_state.draft_iap
    ]
    
    enforce_hitl_dispatch_gate(
        action_plan=approved_actions,
        commander_signature=current_state.approval_signature,
        expected_hash=current_state.plan_hash
    )
    
    logs = actuator_mgr.dispatch_approved_plan(approved_actions, current_state.incident_id)
    
    await ws_broker.broadcast_event(
        current_state.incident_id,
        "AGENT_THOUGHT",
        {"agent": "DispatchManager", "text": f"Successfully actuated {len(logs)} tactical emergency orders."}
    )
    
    return {"status": "DISPATCHED"}

def build_emergency_workflow():
    """
    Compiles the LangGraph StateGraph with interrupt_before=["dispatch_execution_node"].
    Conforms to SDD §5.1.
    """
    workflow = StateGraph(CampusEmergencyState)
    
    workflow.add_node("ingest_incident", ingest_incident_node)
    workflow.add_node("rag_context_retrieval", rag_context_retrieval_node)
    workflow.add_node("parallel_deliberation", parallel_specialist_deliberation_node)
    workflow.add_node("crisis_comms", crisis_comms_node)
    workflow.add_node("safety_guardrail", safety_guardrail_node)
    workflow.add_node("plan_arbitration", plan_arbitration_node)
    workflow.add_node("dispatch_execution_node", dispatch_execution_node)
    
    # Edges
    workflow.add_edge(START, "ingest_incident")
    workflow.add_edge("ingest_incident", "rag_context_retrieval")
    workflow.add_edge("rag_context_retrieval", "parallel_deliberation")
    workflow.add_edge("parallel_deliberation", "crisis_comms")
    workflow.add_edge("crisis_comms", "safety_guardrail")
    workflow.add_edge("safety_guardrail", "plan_arbitration")
    workflow.add_edge("plan_arbitration", "dispatch_execution_node")
    workflow.add_edge("dispatch_execution_node", END)
    
    checkpointer = MemorySaver()
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["dispatch_execution_node"]
    )
    return app

emergency_graph_app = build_emergency_workflow()
