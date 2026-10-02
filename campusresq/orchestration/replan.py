"""
Granular Action Diffing & Replan Engine
Conforms to SDD §5.2 and SRS §5.5.
Allows commander line-item modification and selective re-invocation of dependent sub-agents.
"""

from typing import List, Dict, Any, Optional
from ..models.schemas import CampusEmergencyState, TacticalAction, ActionOverride
from ..agents.evacuation_agent import EvacuationAgent
from ..agents.comms_agent import CrisisPublicCommunicationsAgent
from ..hitl.signature import compute_plan_sha256

async def execute_replan_node(
    state: CampusEmergencyState, 
    feedback_text: str, 
    overrides: Optional[List[ActionOverride]] = None
) -> CampusEmergencyState:
    """
    Selectively re-synthesizes affected sub-plans based on commander feedback
    while preserving unaffected sub-plans.
    """
    state.commander_feedback = feedback_text
    state.iteration_count += 1
    
    # Apply granular line-item overrides directly if provided
    if overrides:
        override_map = {o.action_id: o for o in overrides}
        updated_actions = []
        for act in state.draft_iap:
            if act.action_id in override_map:
                ov = override_map[act.action_id]
                if ov.override_status == "DELETED":
                    continue
                elif ov.override_status == "MODIFIED":
                    if ov.modified_instruction:
                        act.instruction = ov.modified_instruction
                    act.status = "MODIFIED"
                    act.override_notes = ov.human_override_notes or "Commander modified"
                elif ov.override_status == "ACCEPTED":
                    act.status = "APPROVED"
            updated_actions.append(act)
        state.draft_iap = updated_actions

    # Check if feedback targets evacuation routing
    lower_feedback = feedback_text.lower()
    if any(k in lower_feedback for k in ["reroute", "stairs", "exit", "evac", "smoke", "corridor", "hall"]):
        evac_agent = EvacuationAgent()
        new_evac = await evac_agent.run(state)
        state.evacuation_routes = new_evac
        
        # Replace evacuation actions in draft_iap
        non_evac = [a for a in state.draft_iap if a.category != "EVACUATION"]
        new_evac_actions = [TacticalAction(**a) for a in new_evac.get("proposed_actions", [])]
        state.draft_iap = non_evac + new_evac_actions
        
    # Check if feedback targets public communication
    if any(k in lower_feedback for k in ["message", "sms", "alert", "broadcast", "pa", "words"]):
        comms_agent = CrisisPublicCommunicationsAgent()
        new_comms = await comms_agent.run(state)
        state.crisis_communications = new_comms
        
        non_comms = [a for a in state.draft_iap if a.category != "PUBLIC_ALERT"]
        new_comms_actions = [TacticalAction(**a) for a in new_comms.get("proposed_actions", [])]
        state.draft_iap = non_comms + new_comms_actions

    # Recalculate deterministic SHA-256 fingerprint for updated plan
    state.plan_hash = compute_plan_sha256(state.draft_iap)
    state.status = "AWAITING_APPROVAL"
    return state
