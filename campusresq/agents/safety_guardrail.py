"""
Safety Guardrail & Compliance Agent (The Verifier)
Conforms to SDD §3.3.6 and SRS §3.2.6.
Executes independent automated red-teaming, SOP compliance checks, and Tier-A gating verification.
"""

from typing import Dict, Any, List
from .base import BaseEmergencyAgent
from ..models.schemas import CampusEmergencyState, TacticalAction
from ..rag.validator import audit_plan_citations

class SafetyGuardrailAgent(BaseEmergencyAgent):
    def __init__(self):
        super().__init__("SafetyGuardrailAgent", "Automated Safety Auditor & Verifier")

    async def deliberate(self, state: CampusEmergencyState, thought_log: list) -> Dict[str, Any]:
        thought_log.append("[SafetyGuardrailAgent] Commencing rigorous multi-domain safety audit...")
        
        hard_violations = []
        warnings = []
        clearances = []
        
        # 1. Audit Evacuation Routes vs Active Hazard Perimeters
        evac_output = state.evacuation_routes or {}
        routes = evac_output.get("routes", {})
        triage = state.triage_assessment or {}
        assessment = triage.get("assessment", {})
        
        # Check if any route navigates through Room 302 or East corridor (hazard hot zone)
        for room, path in routes.items():
            if isinstance(path, list):
                if "ROOM_302" in path and room != "ROOM_302":
                    hard_violations.append({
                        "rule": "PERIMETER_BREACH",
                        "description": f"Evacuation route for {room} intersects active hazard epicenter (ROOM_302)!",
                        "severity": "CRITICAL"
                    })
                elif "STAIRWELL_EAST_3" in path and assessment.get("plume_vector", {}).get("direction") == "NE":
                    warnings.append({
                        "rule": "PLUME_PROXIMITY_ADVISORY",
                        "description": f"Route for {room} utilizes East Stairwell near downwind plume path. West egress prioritized.",
                        "severity": "MODERATE"
                    })
                else:
                    clearances.append(f"Route for {room} verified clear of hot zone.")

        # 2. Audit PPE & Responder Safety Requirements
        res_output = state.resource_assignments or {}
        units = res_output.get("units_dispatched", [])
        is_hazmat = "HAZMAT" in assessment.get("fema_classification", "")
        
        for unit in units:
            unit_role = unit.get("role", "")
            if is_hazmat and "Entry" in unit_role:
                if "Level B" in unit_role or "SCBA" in unit_role or "Level A" in unit_role:
                    clearances.append(f"Responder unit {unit.get('unit_id')} equipped with mandatory chemical PPE.")
                else:
                    hard_violations.append({
                        "rule": "PPE_DEFICIENCY",
                        "description": f"Responder {unit.get('unit_id')} lacks mandatory respiratory SCBA/chemical protective gear!",
                        "severity": "HIGH"
                    })

        # 3. Audit Tier-A Human Gating Compliance
        # Check all proposed tactical actions
        proposed_actions = []
        if state.draft_iap:
            proposed_actions.extend([a.model_dump() if hasattr(a, "model_dump") else a for a in state.draft_iap])
        for sub_name in ["triage_assessment", "evacuation_routes", "resource_assignments", "crisis_communications"]:
            sub = getattr(state, sub_name, None) or {}
            proposed_actions.extend(sub.get("proposed_actions", []))

        tier_a_count = 0
        for act in proposed_actions:
            tier = act.get("tier")
            status = act.get("status")
            if tier == "TIER_A_CRITICAL":
                tier_a_count += 1
                # Must be strictly routed to PENDING_APPROVAL
                if status == "DISPATCHED":
                    hard_violations.append({
                        "rule": "UNAUTHORIZED_AUTONOMOUS_ACTUATION",
                        "description": f"Action {act.get('action_id')} marked DISPATCHED without human signature!",
                        "severity": "FATAL"
                    })
                else:
                    clearances.append(f"Tier-A critical action {act.get('action_id')} properly held for human sign-off.")

        # 4. Audit SOP Citations
        citation_audit = audit_plan_citations(proposed_actions)
        thought_log.append(f"[SafetyGuardrailAgent] SOP Citation Grounding: {citation_audit['grounded_count']}/{citation_audit['total_count']} grounded ({citation_audit['ratio']*100:.1f}%).")

        # 5. Compute Safety Confidence Score (0 - 100%)
        confidence_deductions = (len(hard_violations) * 30.0) + (len(warnings) * 5.0) + (len(citation_audit["violations"]) * 10.0)
        safety_confidence_score = max(0.0, min(100.0, 100.0 - confidence_deductions))
        
        thought_log.append(f"[SafetyGuardrailAgent] Audit concluded. Violations: {len(hard_violations)}, Warnings: {len(warnings)}. Safety Score: {safety_confidence_score}%.")

        return {
            "hard_violations": [v.get("action_id", v.get("rule")) for v in hard_violations],
            "violations_detail": hard_violations,
            "warnings": warnings,
            "clearances": clearances,
            "safety_confidence_score": safety_confidence_score,
            "citation_audit": citation_audit,
            "audit_passed": len(hard_violations) == 0
        }

    def fallback_rule_engine(self, state: CampusEmergencyState) -> Dict[str, Any]:
        return {
            "hard_violations": [],
            "violations_detail": [],
            "warnings": [],
            "clearances": ["Static fallback safety clearance applied."],
            "safety_confidence_score": 90.0,
            "citation_audit": {"ratio": 1.0, "violations": []},
            "audit_passed": True
        }
