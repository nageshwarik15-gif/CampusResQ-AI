"""
Crisis Public Communications Agent
Conforms to SDD §3.3.5 and SRS §3.2.5.
Synthesizes emergency broadcasts under strict character caps, PA scripts, and Clery Act compliance.
"""

from typing import Dict, Any, List
from .base import BaseEmergencyAgent
from ..models.schemas import CampusEmergencyState, TacticalAction

class CrisisPublicCommunicationsAgent(BaseEmergencyAgent):
    def __init__(self):
        super().__init__("CrisisCommsAgent", "Public Safety Alert Synthesizer")

    async def deliberate(self, state: CampusEmergencyState, thought_log: list) -> Dict[str, Any]:
        building_id = "CHEM_HALL"
        if state.current_telemetry:
            building_id = state.current_telemetry[-1].location.building_id
            
        triage = state.triage_assessment or {}
        assessment = triage.get("assessment", {})
        fema_class = assessment.get("fema_classification", "EMERGENCY_INCIDENT")
        
        thought_log.append(f"[CrisisCommsAgent] Drafting multi-channel alerts for {building_id} ({fema_class}). Enforcing Clery Act standards.")
        
        # 1. Draft SMS: MUST be <= 160 characters, ALL CAPS prefix, actionable imperative instructions, tracking link
        # Example: "CAMPUS EMERGENCY ALERT: Hazard at Chemistry Hall. Evacuate immediately via West exits only. Avoid East wing. Updates: resq.edu/alert"
        bldg_name = "Chem Hall" if "CHEM" in building_id else building_id
        sms_text = f"CAMPUS EMERGENCY ALERT: Hazard at {bldg_name}. Evacuate immediately via West exits only. Avoid East wing. Info: resq.edu/911"
        
        if len(sms_text) > 160:
            sms_text = sms_text[:157] + "..."
            
        thought_log.append(f"[CrisisCommsAgent] Synthesized SMS broadcast ({len(sms_text)}/160 chars): '{sms_text}'")
        
        # 2. Campus PA Audio Siren Script (phonetically clear, instruction repeated twice)
        pa_script = (
            "ATTENTION ALL OCCUPANTS. ATTENTION ALL OCCUPANTS. "
            f"AN EMERGENCY HAS BEEN REPORTED IN {building_id}. "
            "EVACUATE IMMEDIATELY USING WEST STAIRWELLS AND EXITS. "
            "DO NOT USE ELEVATORS. AVOID THE EAST WING. "
            "I REPEAT: EVACUATE IMMEDIATELY USING WEST STAIRWELLS AND EXITS. DO NOT USE ELEVATORS."
        )
        thought_log.append("[CrisisCommsAgent] Generated dual-iteration phonetic acoustic PA script.")
        
        # 3. Emergency Website Banner / Email Text
        web_banner = {
            "headline": f"URGENT: Active Emergency at {bldg_name}",
            "severity": "CRITICAL",
            "evac_zone": "Chemistry Hall & West Quad",
            "instructions": "All personnel avoid Chemistry Hall perimeter (150m radius). Evacuees muster at West Quad.",
            "clery_compliant": True
        }
        
        # Tactical Actions: Mass SMS is TIER_A_CRITICAL (requires human sign-off!)
        proposed_actions = [
            TacticalAction(
                action_id="ACT_COMMS_01",
                tier="TIER_A_CRITICAL",
                priority="P1_IMMEDIATE",
                category="PUBLIC_ALERT",
                target="Campus Emergency Notification System (SMS / Push)",
                instruction=sms_text,
                rationale="Mandatory Clery Act urgent alert to protect human life without speculative details.",
                sop_citation={
                    "document_title": "Crisis Communications & Clery Act Emergency Notification",
                    "section": "3.4.1",
                    "page": 58
                }
            ),
            TacticalAction(
                action_id="ACT_COMMS_02",
                tier="TIER_A_CRITICAL",
                priority="P1_IMMEDIATE",
                category="PUBLIC_ALERT",
                target="Campus PA Acoustic Siren Matrix",
                instruction=pa_script,
                rationale="Direct audio audible broadcast to occupants currently in physical structure.",
                sop_citation={
                    "document_title": "Crisis Communications & Clery Act Emergency Notification",
                    "section": "3.4.1",
                    "page": 58
                }
            )
        ]
        
        return {
            "sms_broadcast": sms_text,
            "sms_length": len(sms_text),
            "pa_script": pa_script,
            "web_banner": web_banner,
            "proposed_actions": [a.model_dump() for a in proposed_actions]
        }

    def fallback_rule_engine(self, state: CampusEmergencyState) -> Dict[str, Any]:
        sms = "CAMPUS EMERGENCY ALERT: Emergency at Chem Hall. Evacuate via nearest exit. Do not use elevators. resq.edu/alert"
        return {
            "sms_broadcast": sms,
            "sms_length": len(sms),
            "pa_script": "ATTENTION. EVACUATE THE BUILDING IMMEDIATELY. DO NOT USE ELEVATORS.",
            "proposed_actions": [
                {
                    "action_id": "ACT_FALLBACK_COMMS_01",
                    "tier": "TIER_A_CRITICAL",
                    "priority": "P1_IMMEDIATE",
                    "category": "PUBLIC_ALERT",
                    "target": "Campus Emergency SMS",
                    "instruction": sms,
                    "rationale": "Fallback standard alert text.",
                    "sop_citation": {
                        "document_title": "Crisis Communications & Clery Act Emergency Notification",
                        "section": "3.4.1",
                        "page": 58
                    }
                }
            ]
        }
