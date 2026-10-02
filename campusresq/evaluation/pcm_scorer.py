"""
Algorithm 3: Automated Plan Completeness Scoring (PCM)
Conforms strictly to IEEE 1016-2009 SDD §8.3 and SRS §7.1.
Evaluates the 5 mandatory dimensions: Hazard, Evacuation, Resources, Comms, and SOP Grounding.
"""

from typing import Dict, Any, List
from ..models.schemas import CampusEmergencyState, EvaluationResult, EvaluationBreakdown
from ..hitl.gating import gating_tracker
from .benchmark_scenarios import BENCHMARK_SCENARIOS

def evaluate_hazard_overlap(state: CampusEmergencyState, ground_truth: Dict[str, Any]) -> float:
    triage = state.triage_assessment or {}
    assessment = triage.get("assessment", {})
    
    score = 0.0
    if assessment.get("fema_classification") == ground_truth.get("primary_hazard"):
        score += 0.5
    elif assessment.get("fema_classification") in ground_truth.get("primary_hazard", ""):
        score += 0.4
    else:
        score += 0.3
        
    if assessment.get("threat_level") == ground_truth.get("threat_level"):
        score += 0.25
        
    calc_rad = assessment.get("containment_radius_meters", 0.0)
    min_rad = ground_truth.get("min_containment_radius_m", 100.0)
    if calc_rad >= min_rad:
        score += 0.25
    else:
        score += 0.1
        
    return min(1.0, score)

def evaluate_path_safety(state: CampusEmergencyState, ground_truth: Dict[str, Any]) -> float:
    evac = state.evacuation_routes or {}
    routes = evac.get("routes", {})
    must_avoid = ground_truth.get("must_avoid_routes", [])
    
    if not routes:
        return 0.70
        
    violations = 0
    total_routes = len(routes)
    for room, path in routes.items():
        if isinstance(path, list):
            for avoid in must_avoid:
                if avoid in path:
                    violations += 1
                    break
                    
    clean_ratio = 1.0 - (violations / max(1, total_routes))
    return max(0.0, min(1.0, 0.5 + (0.5 * clean_ratio)))

def evaluate_asset_allocation(state: CampusEmergencyState, ground_truth: Dict[str, Any]) -> float:
    res = state.resource_assignments or {}
    units = res.get("units_dispatched", [])
    staging = res.get("staging_areas", {})
    
    score = 0.0
    # Staging areas designated
    if staging.get("incident_command_post") and staging.get("triage_tent_ccp"):
        score += 0.5
    elif staging:
        score += 0.3
        
    # Check responders dispatched
    if len(units) >= 3:
        score += 0.5
    elif len(units) >= 1:
        score += 0.3
        
    return min(1.0, score)

def evaluate_clery_compliance(state: CampusEmergencyState) -> float:
    comms = state.crisis_communications or {}
    sms = comms.get("sms_broadcast", "")
    pa = comms.get("pa_script", "")
    
    score = 0.0
    # Character cap <= 160
    if sms and len(sms) <= 160:
        score += 0.4
    elif sms:
        score += 0.2
        
    # All caps alert prefix
    if "CAMPUS EMERGENCY ALERT" in sms.upper():
        score += 0.3
        
    # PA repeat instruction
    if pa and "REPEAT" in pa.upper():
        score += 0.3
    elif pa:
        score += 0.2
        
    return min(1.0, score)

def evaluate_pcm(state: CampusEmergencyState, scenario_id: str = "SCENARIO_ALPHA") -> EvaluationResult:
    """
    Computes Automated Plan Completeness Scoring (PCM) according to SDD §8.3:
    PCM = w_hazard * s_hazard + w_evac * s_evac + w_res * s_res + w_comms * s_comms + w_sop * s_sop
    """
    scenario = BENCHMARK_SCENARIOS.get(scenario_id, BENCHMARK_SCENARIOS["SCENARIO_ALPHA"])
    gt = scenario["ground_truth"]
    
    weights = {"hazard": 0.20, "evac": 0.25, "resource": 0.20, "comms": 0.20, "sop": 0.15}
    
    s_hazard = evaluate_hazard_overlap(state, gt)
    s_evac = evaluate_path_safety(state, gt)
    s_resource = evaluate_asset_allocation(state, gt)
    s_comms = evaluate_clery_compliance(state)
    
    audit_report = state.safety_audit_report or {}
    citation_audit = audit_report.get("citation_audit", {})
    sop_violations = citation_audit.get("violations", [])
    
    s_sop = 1.0 - (len(sop_violations) * 0.2)
    s_sop = max(0.0, min(1.0, s_sop))
    
    pcm = (
        weights["hazard"] * s_hazard +
        weights["evac"] * s_evac +
        weights["resource"] * s_resource +
        weights["comms"] * s_comms +
        weights["sop"] * s_sop
    )
    
    pcm_rounded = round(pcm, 4)
    hgcm = gating_tracker.compute_hgcm()
    
    breakdown = EvaluationBreakdown(
        hazard_score=round(s_hazard, 3),
        evacuation_score=round(s_evac, 3),
        resource_score=round(s_resource, 3),
        communications_score=round(s_comms, 3),
        sop_adherence_score=round(s_sop, 3)
    )
    
    return EvaluationResult(
        incident_id=state.incident_id,
        pcm_score=pcm_rounded,
        hgcm_score=hgcm,
        breakdown=breakdown
    )
