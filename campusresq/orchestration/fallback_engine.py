"""
Deterministic Safe-Fail Fallback Mode Engine
Conforms strictly to IEEE 1016-2009 SDD §9.2 and SRS §2.5, §6.4.
Provides zero-hanging rule-based contingencies for when LLM or network latency exceeds 12s.
"""

from typing import Dict, Any, List
from ..models.schemas import TacticalAction

FALLBACK_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "CHEM_HALL": {
        "template_id": "TEMPLATE_104_HAZMAT_CHEM_HALL",
        "description": "Deterministic Standard Evacuation Template #104 for Chemistry Hall",
        "actions": [
            TacticalAction(
                action_id="FALLBACK_ACT_01",
                tier="TIER_A_CRITICAL",
                priority="P1_IMMEDIATE",
                category="EVACUATION",
                target="Chemistry Hall - All Floors",
                instruction="Evacuate all occupants via exterior stairwells immediately; mechanical elevators locked at Ground Floor.",
                rationale="Failsafe standard operating procedure for toxic solvent releases.",
                sop_citation={
                    "document_title": "Hazardous Material Incident Protocol",
                    "section": "4.3.2",
                    "page": 87
                }
            ),
            TacticalAction(
                action_id="FALLBACK_ACT_02",
                tier="TIER_A_CRITICAL",
                priority="P1_IMMEDIATE",
                category="PUBLIC_ALERT",
                target="Campus Emergency Notification System",
                instruction="CAMPUS EMERGENCY ALERT: Hazmat emergency at Chem Hall. Evacuate area immediately. Stand clear 150m.",
                rationale="Clery Act immediate life safety warning.",
                sop_citation={
                    "document_title": "Crisis Communications & Clery Act Emergency Notification",
                    "section": "3.4.1",
                    "page": 58
                }
            ),
            TacticalAction(
                action_id="FALLBACK_ACT_03",
                tier="TIER_B_OPERATIONAL",
                priority="P1_IMMEDIATE",
                category="HAZMAT",
                target="Chemistry Hall Exterior",
                instruction="Establish 150m exclusion perimeter; dispatch Engine-4 with dry chemical foam.",
                rationale="Prevent unequipped personnel from entering toxic vapor plume.",
                sop_citation={
                    "document_title": "Hazardous Material Incident Protocol",
                    "section": "4.3.2",
                    "page": 87
                }
            )
        ]
    },
    "NORTH_DINING": {
        "template_id": "TEMPLATE_201_ACTIVE_HOSTILE",
        "description": "Deterministic Lockdown & Tactical Response Template #201",
        "actions": [
            TacticalAction(
                action_id="FALLBACK_ACT_11",
                tier="TIER_A_CRITICAL",
                priority="P1_IMMEDIATE",
                category="LOCKDOWN",
                target="North Dining Commons & Library",
                instruction="Trigger immediate magnetic perimeter lockdown on North Dining Commons and University Library.",
                rationale="Isolate hostile threat and protect adjacent high-density buildings.",
                sop_citation={
                    "document_title": "Active Threat & Hostile Intruder Protocol",
                    "section": "5.2.1",
                    "page": 112
                }
            ),
            TacticalAction(
                action_id="FALLBACK_ACT_12",
                tier="TIER_A_CRITICAL",
                priority="P1_IMMEDIATE",
                category="PUBLIC_ALERT",
                target="Campus Emergency Notification System",
                instruction="CAMPUS EMERGENCY ALERT: Active threat near North Dining. RUN, HIDE, FIGHT. Avoid area. Updates to follow.",
                rationale="Urgent protective warning.",
                sop_citation={
                    "document_title": "Crisis Communications & Clery Act Emergency Notification",
                    "section": "3.4.1",
                    "page": 58
                }
            )
        ]
    }
}

def get_fallback_iap(building_id: str = "CHEM_HALL") -> Dict[str, Any]:
    bldg_key = "CHEM_HALL" if "CHEM" in building_id.upper() else ("NORTH_DINING" if "DINING" in building_id.upper() or "LIB" in building_id.upper() else "CHEM_HALL")
    template = FALLBACK_TEMPLATES.get(bldg_key, FALLBACK_TEMPLATES["CHEM_HALL"])
    return {
        "fallback_active": True,
        "template_id": template["template_id"],
        "description": template["description"],
        "tactical_actions": [a.model_dump() for a in template["actions"]]
    }
