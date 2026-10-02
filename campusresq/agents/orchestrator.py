"""
Incident Orchestrator Agent (Master Coordinator)
Conforms to SDD §3.3.1 and SRS §3.2.1.
Enforces FEMA NIMS ICS-202/204 structure and manages global state lifecycle.
"""

from typing import Dict, Any, List
from .base import BaseEmergencyAgent
from ..models.schemas import (
    CampusEmergencyState, 
    TacticalAction, 
    IncidentActionPlan, 
    IncidentClassification,
    current_iso_time
)
from ..orchestration.arbitration import arbitrate_and_prioritize

class IncidentOrchestratorAgent(BaseEmergencyAgent):
    def __init__(self):
        super().__init__("IncidentOrchestrator", "Master Incident Coordinator")

    async def deliberate(self, state: CampusEmergencyState, thought_log: list) -> Dict[str, Any]:
        thought_log.append(f"[IncidentOrchestrator] Consolidating specialist outputs for incident '{state.incident_id}'...")
        
        # 1. Collect all sub-agent tactical actions
        proposed_actions = []
        for sub_name in ["triage_assessment", "evacuation_routes", "resource_assignments", "crisis_communications"]:
            sub = getattr(state, sub_name, None) or {}
            for act_dict in sub.get("proposed_actions", []):
                proposed_actions.append(TacticalAction(**act_dict) if isinstance(act_dict, dict) else act_dict)

        # 2. Run Algorithm 2: Multi-Agent Conflict Arbitration & Priority Sorting
        audit_report = state.safety_audit_report or {}
        hard_violations = set(audit_report.get("hard_violations", []))
        
        class MockSubPlans:
            def __init__(self, actions):
                self.actions = actions
                
        class MockAudit:
            def __init__(self, violations):
                self.hard_violations = violations
                
        prioritized_actions = arbitrate_and_prioritize(
            all_actions=proposed_actions,
            hard_violations=hard_violations
        )
        
        thought_log.append(f"[IncidentOrchestrator] Conflict arbitration resolved. Compiled {len(prioritized_actions)} prioritized tactical actions.")
        
        # 3. Build Incident Classification
        triage = (state.triage_assessment or {}).get("assessment", {})
        classification = IncidentClassification(
            primary_type=triage.get("fema_classification", "HAZMAT_SPILL_CLASS_B"),
            severity_level=triage.get("threat_level", "CRITICAL"),
            affected_perimeter_meters=triage.get("containment_radius_meters", 150.0)
        )
        
        # 4. Generate FEMA ICS-202/204 Incident Action Plan
        confidence = (state.safety_audit_report or {}).get("safety_confidence_score", 95.0) / 100.0
        iap = IncidentActionPlan(
            plan_id=f"iap_{state.incident_id[:8]}",
            incident_id=state.incident_id,
            version=state.iteration_count + 1,
            generated_at=current_iso_time(),
            status="draft_pending_review",
            confidence_score=round(confidence, 2),
            incident_classification=classification,
            tactical_actions=prioritized_actions
        )
        
        return {
            "draft_iap": prioritized_actions,
            "incident_action_plan": iap.model_dump(),
            "status": "AWAITING_APPROVAL"
        }

    def fallback_rule_engine(self, state: CampusEmergencyState) -> Dict[str, Any]:
        return {
            "draft_iap": [],
            "incident_action_plan": {},
            "status": "AWAITING_APPROVAL"
        }
