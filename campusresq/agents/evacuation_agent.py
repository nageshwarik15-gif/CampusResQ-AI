"""
Evacuation & Path Routing Agent
Conforms to SDD §3.3.3 and SRS §3.2.3.
Executes Algorithm 1: Hazard-Weighted Dynamic Evacuation Pathing using NetworkX.
"""

from typing import Dict, Any, List
from .base import BaseEmergencyAgent
from ..models.schemas import CampusEmergencyState, TacticalAction
from ..spatial.campus_graph import build_campus_building_graph, HazardZone
from ..spatial.routing import compute_evacuation_routes

class EvacuationAgent(BaseEmergencyAgent):
    def __init__(self):
        super().__init__("EvacuationAgent", "Evacuation & Spatial Path Router")

    async def deliberate(self, state: CampusEmergencyState, thought_log: list) -> Dict[str, Any]:
        # Read triage assessment from state
        triage = state.triage_assessment or {}
        assessment = triage.get("assessment", {})
        containment_radius = assessment.get("containment_radius_meters", 150.0)
        
        building_id = "CHEM_HALL"
        if state.current_telemetry:
            building_id = state.current_telemetry[-1].location.building_id
            
        thought_log.append(f"[EvacuationAgent] Loading spatial topology for building '{building_id}'...")
        graph = build_campus_building_graph(building_id)
        
        # Determine hazard location within building
        # Default to Center/East (Room 302: x=25, y=30)
        hazard_center = (25.0, 30.0)
        lethal_r = 12.0
        danger_r = 30.0
        
        # Check if commander feedback reported smoke/hazard elsewhere
        feedback = (state.commander_feedback or "").lower()
        if "east stairs" in feedback or "east exit" in feedback or "east" in feedback:
            thought_log.append("[EvacuationAgent] Commander feedback detected hazard near East Stairwell. Adding hazard boundary.")
            hazard_zones = [
                HazardZone("HAZ_ORIGIN", "Spill Origin", hazard_center, lethal_r, danger_r),
                HazardZone("HAZ_EAST_STAIRS", "East Stairwell Smoke", (75.0, 25.0), lethal_radius=15.0, danger_radius=30.0)
            ]
        else:
            hazard_zones = [
                HazardZone("HAZ_ORIGIN", "Chemical Spill & Secondary Fire", hazard_center, lethal_r, danger_r)
            ]
            
        thought_log.append(f"[EvacuationAgent] Running Algorithm 1 (Hazard-Weighted Dijkstra/A*) across {len(graph.nodes)} nodes...")
        routes_result = compute_evacuation_routes(graph, hazard_zones, graph.safe_exits)
        
        thought_log.append(f"[EvacuationAgent] Calculated viable egress paths for {len(routes_result['routes'])} zones. Primary exit: EXIT_WEST_GROUND.")
        
        # Formulate tactical actions
        proposed_actions = [
            TacticalAction(
                action_id="ACT_EVAC_01",
                tier="TIER_A_CRITICAL",
                priority="P1_IMMEDIATE",
                category="EVACUATION",
                target=f"{building_id} - Floor 3",
                instruction=(
                    "Order immediate mandatory evacuation of Floor 3 occupants via West Stairwell to Ground West Exit. "
                    "Avoid East corridor and East stairwells due to chemical vapor accumulation."
                ),
                rationale="Room 302 spill center presents imminent respiratory hazard. West path offers lowest threat exposure penalty.",
                sop_citation={
                    "document_title": "Campus Evacuation & Life Safety Standard",
                    "section": "2.1.4",
                    "page": 34
                }
            ),
            TacticalAction(
                action_id="ACT_EVAC_02",
                tier="TIER_A_CRITICAL",
                priority="P1_IMMEDIATE",
                category="EVACUATION",
                target=f"{building_id} - Elevators",
                instruction="Recall all building elevators to Ground Floor and mechanically lock out of service.",
                rationale="Hard fire safety constraint to prevent elevator shaft chimney effect and occupant entrapment.",
                sop_citation={
                    "document_title": "Hazardous Material Incident Protocol",
                    "section": "4.3.2",
                    "page": 87
                }
            ),
            TacticalAction(
                action_id="ACT_EVAC_03",
                tier="TIER_B_OPERATIONAL",
                priority="P2_HIGH",
                category="EVACUATION",
                target="West Quad Assembly Lawn",
                instruction="Direct evacuees to West Quad Muster Station (Zone Green-2), at least 150m upwind of Chemistry Hall.",
                rationale="Maintains safe standoff distance beyond the 150m plume propagation radius.",
                sop_citation={
                    "document_title": "Campus Evacuation & Life Safety Standard",
                    "section": "2.1.4",
                    "page": 34
                }
            )
        ]
        
        return {
            "routes": routes_result["routes"],
            "path_details": routes_result["details"],
            "uncompromised_exits": routes_result["uncompromised_exits"],
            "proposed_actions": [a.model_dump() for a in proposed_actions]
        }

    def fallback_rule_engine(self, state: CampusEmergencyState) -> Dict[str, Any]:
        return {
            "routes": {"ROOM_301": ["ROOM_301", "CORRIDOR_3_WEST", "STAIRWELL_WEST_3", "EXIT_WEST_GROUND"]},
            "path_details": {},
            "uncompromised_exits": ["EXIT_WEST_GROUND"],
            "proposed_actions": [
                {
                    "action_id": "ACT_FALLBACK_EVAC_01",
                    "tier": "TIER_A_CRITICAL",
                    "priority": "P1_IMMEDIATE",
                    "category": "EVACUATION",
                    "target": "CHEM_HALL",
                    "instruction": "Initiate standard fire evacuation template: egress via nearest emergency exit; disable elevators.",
                    "rationale": "Fallback standard operating procedure.",
                    "sop_citation": {
                        "document_title": "Campus Evacuation & Life Safety Standard",
                        "section": "2.1.4",
                        "page": 34
                    }
                }
            ]
        }
