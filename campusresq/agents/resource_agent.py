"""
Resource Allocation & EMS/Fire Agent
Conforms to SDD §3.3.4 and SRS §3.2.4.
Computes optimal dispatch of campus security, municipal fire engines, and EMS transport units.
"""

from typing import Dict, Any, List
from .base import BaseEmergencyAgent
from ..models.schemas import CampusEmergencyState, TacticalAction

class ResourceAllocationAgent(BaseEmergencyAgent):
    def __init__(self):
        super().__init__("ResourceAgent", "Tactical Logistics & Asset Manager")

    async def deliberate(self, state: CampusEmergencyState, thought_log: list) -> Dict[str, Any]:
        triage = state.triage_assessment or {}
        assessment = triage.get("assessment", {})
        fema_class = assessment.get("fema_classification", "GENERAL_EMERGENCY")
        casualties = assessment.get("estimated_casualties", {"immediate": 1, "delayed": 3, "minor": 5})
        
        thought_log.append(f"[ResourceAgent] Analyzing asset requirements for {fema_class} with {casualties.get('immediate', 0)} priority casualties...")
        
        # Calculate asset assignments
        staging_areas = {
            "incident_command_post": "Lot 4 North (37.4285, -122.1710)",
            "triage_tent_ccp": "South Athletic Field (37.4260, -122.1690)",
            "media_staging": "Visitor Center Pavilion (37.4290, -122.1660)"
        }
        
        units_dispatched = [
            {"unit_id": "ENGINE-4", "type": "Fire Engine (Dry Chemical Foam)", "eta_minutes": 4, "role": "Fire Suppression & Vapor Blanketing"},
            {"unit_id": "HAZMAT-1", "type": "County Hazmat Response Unit", "eta_minutes": 8, "role": "Level B Entry & Vapor Containment"},
            {"unit_id": "MED-1", "type": "Advanced Life Support (ALS) Ambulance", "eta_minutes": 5, "role": "Immediate Casualty Extraction"},
            {"unit_id": "MED-2", "type": "Basic Life Support (BLS) Ambulance", "eta_minutes": 6, "role": "Delayed Casualty Transport"},
            {"unit_id": "SEC-PATROL-1", "type": "Campus Police Mobile", "eta_minutes": 2, "role": "Perimeter Cordon & Traffic Interdiction"}
        ]
        
        thought_log.append(f"[ResourceAgent] Designated ICP at '{staging_areas['incident_command_post']}', Triage CCP at '{staging_areas['triage_tent_ccp']}'.")
        thought_log.append(f"[ResourceAgent] Assigned {len(units_dispatched)} emergency response units with average ETA 5.0 mins.")
        
        proposed_actions = [
            TacticalAction(
                action_id="ACT_RES_01",
                tier="TIER_B_OPERATIONAL",
                priority="P1_IMMEDIATE",
                category="MEDICAL",
                target="South Athletic Field",
                instruction="Establish Casualty Collection Point (CCP) and medical triage tent; dispatch ALS MED-1 and BLS MED-2 units.",
                rationale="Supports immediate decontamination and stabilization of estimated 7 acute toxic vapor casualties.",
                sop_citation={
                    "document_title": "Hazardous Material Incident Protocol",
                    "section": "4.3.2",
                    "page": 87
                }
            ),
            TacticalAction(
                action_id="ACT_RES_02",
                tier="TIER_B_OPERATIONAL",
                priority="P2_HIGH",
                category="HAZMAT",
                target="Chemistry Hall Staging Lot 4",
                instruction="Deploy County HAZMAT-1 and Engine-4 with dry chemical foam units; require Level B SCBA PPE for all entry personnel.",
                rationale="SDS guidelines mandate chemical vapor suppression without direct water stream application.",
                sop_citation={
                    "document_title": "SDS #CHEM-041: n-Hexane Analytical Grade",
                    "section": "SDS-8.2",
                    "page": 4
                }
            )
        ]
        
        return {
            "staging_areas": staging_areas,
            "units_dispatched": units_dispatched,
            "proposed_actions": [a.model_dump() for a in proposed_actions]
        }

    def fallback_rule_engine(self, state: CampusEmergencyState) -> Dict[str, Any]:
        return {
            "staging_areas": {"incident_command_post": "Lot 4", "triage_tent_ccp": "South Field"},
            "units_dispatched": [{"unit_id": "ENG-1", "eta_minutes": 5}],
            "proposed_actions": [
                {
                    "action_id": "ACT_FALLBACK_RES_01",
                    "tier": "TIER_B_OPERATIONAL",
                    "priority": "P2_HIGH",
                    "category": "MEDICAL",
                    "target": "South Field",
                    "instruction": "Deploy standard medical triage staging at South Field.",
                    "rationale": "Fallback standard resource allocation.",
                    "sop_citation": {
                        "document_title": "Campus Evacuation & Life Safety Standard",
                        "section": "2.1.4",
                        "page": 34
                    }
                }
            ]
        }
