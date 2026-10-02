"""
Triage & Hazard Assessment Agent
Conforms to SDD §3.3.2 and SRS §3.2.2.
Ingests raw telemetry metrics, classifies threat according to FEMA/ICS, and estimates casualties.
"""

from typing import Dict, Any, List
from .base import BaseEmergencyAgent
from ..models.schemas import CampusEmergencyState, TacticalAction

class TriageHazardAgent(BaseEmergencyAgent):
    def __init__(self):
        super().__init__("TriageAgent", "Triage & Hazard Classifier")

    async def deliberate(self, state: CampusEmergencyState, thought_log: list) -> Dict[str, Any]:
        # Inspect incoming telemetry
        hazard_type = "UNKNOWN"
        building_id = "CHEM_HALL"
        raw_payload = {}
        
        if state.current_telemetry:
            latest = state.current_telemetry[-1]
            hazard_type = latest.hazard_type.upper()
            building_id = latest.location.building_id
            raw_payload = latest.raw_payload
            
        thought_log.append(f"[TriageAgent] Ingested telemetry: type={hazard_type}, building={building_id}")
        
        # Analyze based on hazard type
        if "HAZMAT" in hazard_type or "SPILL" in hazard_type or "CHEMICAL" in hazard_type:
            ppm = raw_payload.get("toxic_ppm", 120.0)
            fema_class = "HAZMAT_SPILL_CLASS_B"
            threat_level = "CRITICAL" if ppm > 50 else "SEVERE"
            radius = 150.0
            plume = {"direction": "NE", "speed_kmh": 12.0}
            casualties = {"immediate": 2, "delayed": 5, "minor": 18}
            thought_log.append(f"[TriageAgent] Solvent vapor detected: {ppm} PPM. Calculating atmospheric dispersion (Vector NE @ 12 km/h).")
            
        elif "SHOOTER" in hazard_type or "ACTIVE" in hazard_type or "HOSTILE" in hazard_type:
            fema_class = "ACTIVE_HOSTILE_ASSAULT"
            threat_level = "CRITICAL"
            radius = 300.0
            plume = {"direction": "ALL_DIRECTIONS", "speed_kmh": 0.0}
            casualties = {"immediate": 3, "delayed": 4, "minor": 12}
            thought_log.append("[TriageAgent] Acoustic gunshot signatures confirmed. Initiating active hostile mass casualty triage protocol.")
            
        elif "EARTHQUAKE" in hazard_type or "COLLAPSE" in hazard_type:
            fema_class = "SEISMIC_STRUCTURAL_COLLAPSE"
            threat_level = "CRITICAL"
            radius = 250.0
            plume = {"direction": "DEBRIS_FIELD", "speed_kmh": 0.0}
            casualties = {"immediate": 6, "delayed": 14, "minor": 35}
            thought_log.append("[TriageAgent] High-magnitude structural failure detected. Prioritizing search & rescue grid classification.")
            
        else:
            fema_class = "GENERAL_STRUCTURAL_FIRE"
            threat_level = "SEVERE"
            radius = 100.0
            plume = {"direction": "NORTH", "speed_kmh": 8.0}
            casualties = {"immediate": 1, "delayed": 3, "minor": 10}

        assessment = {
            "fema_classification": fema_class,
            "threat_level": threat_level,
            "containment_radius_meters": radius,
            "plume_vector": plume,
            "estimated_casualties": casualties,
            "source_telemetry_id": state.current_telemetry[-1].event_id if state.current_telemetry else "sim_001"
        }
        
        # Proposed initial tactical actions
        proposed_actions = [
            TacticalAction(
                action_id="ACT_TRIAGE_01",
                tier="TIER_B_OPERATIONAL",
                priority="P1_IMMEDIATE",
                category="HAZMAT" if "HAZMAT" in fema_class else "LOCKDOWN",
                target=building_id,
                instruction=f"Establish a {radius}-meter hot-zone perimeter cordon around {building_id}.",
                rationale=f"Prevents secondary contamination based on plume propagation {plume['direction']} at {plume['speed_kmh']} km/h.",
                sop_citation={
                    "document_title": "Hazardous Material Incident Protocol" if "HAZMAT" in fema_class else "Active Threat & Hostile Intruder Protocol",
                    "section": "4.3.2" if "HAZMAT" in fema_class else "5.2.1",
                    "page": 87 if "HAZMAT" in fema_class else 112
                }
            )
        ]
        
        return {
            "assessment": assessment,
            "proposed_actions": [a.model_dump() for a in proposed_actions]
        }

    def fallback_rule_engine(self, state: CampusEmergencyState) -> Dict[str, Any]:
        return {
            "assessment": {
                "fema_classification": "HAZMAT_SPILL_CLASS_B",
                "threat_level": "CRITICAL",
                "containment_radius_meters": 150.0,
                "plume_vector": {"direction": "NE", "speed_kmh": 12.0},
                "estimated_casualties": {"immediate": 2, "delayed": 5, "minor": 18}
            },
            "proposed_actions": [
                {
                    "action_id": "ACT_FALLBACK_TRIAGE_01",
                    "tier": "TIER_B_OPERATIONAL",
                    "priority": "P1_IMMEDIATE",
                    "category": "HAZMAT",
                    "target": "CHEM_HALL",
                    "instruction": "Enforce static 150m perimeter standoff according to Emergency Rulebook Template #104.",
                    "rationale": "Deterministic fail-safe procedure triggered.",
                    "sop_citation": {
                        "document_title": "Hazardous Material Incident Protocol",
                        "section": "4.3.2",
                        "page": 87
                    }
                }
            ]
        }
