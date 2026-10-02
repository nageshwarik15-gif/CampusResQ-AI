import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from campusresq.api.app import app
from campusresq.models.schemas import CampusEmergencyState, TelemetryEvent, LocationModel, TacticalAction
from campusresq.storage.db import db
from campusresq.hitl.signature import compute_plan_sha256, commander_key_mgr

client = TestClient(app)

def test_health_and_readiness_probes():
    """Verify healthz and readyz endpoints (SDD §10.2)."""
    res_health = client.get("/healthz")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "HEALTHY"
    assert data_health["service"] == "CampusResQ_AI"

    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200
    data_ready = res_ready.json()
    assert data_ready["status"] == "READY"
    assert data_ready["indexed_rag_documents"] > 0

def test_dashboard_root():
    """Verify the root endpoint serves the incident commander cockpit."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "CampusResQ" in res.text

def test_incident_ingest_and_state():
    """Verify emergency event ingestion and retrieval (SDD §7.1.1, §7.1.2)."""
    payload = {
        "incident_id": "test_api_inc_001",
        "source_type": "iot_sensor",
        "location": {
            "campus_zone": "SCIENCE_QUAD",
            "building_id": "CHEM_HALL",
            "floor": 3,
            "room": "ROOM_302",
            "lat": 37.4278,
            "lng": -122.1695
        },
        "raw_data": {
            "hazard_indicators": ["FLAMMABLE_VAPOR_DETECTED"],
            "toxic_ppm": 120.0
        }
    }
    
    res = client.post("/api/v1/incidents/ingest", json=payload)
    assert res.status_code == 202
    data = res.json()
    assert data["incident_id"] == "test_api_inc_001"
    assert data["status"] == "PROCESSING"

    # Fetch incident state
    res_state = client.get("/api/v1/incidents/test_api_inc_001/state")
    assert res_state.status_code == 200
    state_data = res_state.json()
    assert state_data["incident_id"] == "test_api_inc_001"

def test_commander_credentials_and_signing():
    """Verify commander public key and digital signing utility."""
    res_creds = client.get("/api/v1/commander/credentials")
    assert res_creds.status_code == 200
    creds = res_creds.json()
    assert "public_key_pem" in creds
    assert creds["commander_id"] == "CHIEF_MILLER_01"

    # Test signing endpoint
    sample_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    res_sign = client.post("/api/v1/commander/sign", json={"plan_hash": sample_hash})
    assert res_sign.status_code == 200
    sign_data = res_sign.json()
    assert "digital_signature" in sign_data
    assert sign_data["plan_hash"] == sample_hash

def test_human_approval_and_gating():
    """Verify approval endpoint with signature verification and gating enforcement (SDD §7.1.3)."""
    inc_id = "test_api_approval_inc"
    action = TacticalAction(
        action_id="ACT_TEST_TIER_A",
        tier="TIER_A_CRITICAL",
        priority="P1_IMMEDIATE",
        category="EVACUATION",
        target="Floor 3",
        instruction="Evacuate Floor 3",
        rationale="Life safety"
    )
    plan_hash = compute_plan_sha256([action])
    
    state = CampusEmergencyState(
        incident_id=inc_id,
        status="AWAITING_APPROVAL",
        draft_iap=[action],
        plan_hash=plan_hash
    )
    db.save_incident_state(state)

    # 1. Attempt with invalid signature -> 403 Forbidden
    res_fail = client.post(f"/api/v1/incidents/{inc_id}/approve", json={
        "plan_id": inc_id,
        "commander_id": "CHIEF_MILLER_01",
        "decision": "APPROVED_ALL",
        "digital_signature": "INVALID_FORGED_SIGNATURE=="
    })
    assert res_fail.status_code == 403
    assert "Invalid cryptographic signature" in res_fail.json()["detail"]

    # 2. Attempt with valid signature -> 200 OK & Dispatched
    valid_sig = commander_key_mgr.sign_plan_hash(plan_hash)
    res_ok = client.post(f"/api/v1/incidents/{inc_id}/approve", json={
        "plan_id": inc_id,
        "commander_id": "CHIEF_MILLER_01",
        "decision": "APPROVED_ALL",
        "digital_signature": valid_sig
    })
    assert res_ok.status_code == 200
    data_ok = res_ok.json()
    assert data_ok["status"] == "DISPATCHING"
    assert data_ok["approved_count"] == 1
    assert len(data_ok["dispatch_receipts"]) == 1

def test_replan_feedback_loop():
    """Verify ReplanNode feedback loop when commander requests redraft (SDD §5.2)."""
    inc_id = "test_api_replan_inc"
    action = TacticalAction(
        action_id="ACT_TEST_EVAC",
        tier="TIER_A_CRITICAL",
        priority="P1_IMMEDIATE",
        category="EVACUATION",
        target="Chemistry Hall",
        instruction="Evacuate via East corridor",
        rationale="Egress"
    )
    plan_hash = compute_plan_sha256([action])
    state = CampusEmergencyState(
        incident_id=inc_id,
        status="AWAITING_APPROVAL",
        draft_iap=[action],
        plan_hash=plan_hash
    )
    db.save_incident_state(state)

    res = client.post(f"/api/v1/incidents/{inc_id}/approve", json={
        "plan_id": inc_id,
        "commander_id": "CHIEF_MILLER_01",
        "decision": "REJECTED_REDRAFT_REQUESTED",
        "feedback_text": "East stairs smoky, reroute to West exit only"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REPLANNED"
    assert data["iteration_count"] == 1
    assert data["plan_hash"] is not None

def test_dynamic_event_injection():
    """Verify live event injection and dynamic replan trigger (FR-1.3)."""
    inc_id = "test_api_inject_inc"
    state = CampusEmergencyState(
        incident_id=inc_id,
        status="ACTIVE",
        current_telemetry=[
            TelemetryEvent(
                source="iot",
                location=LocationModel(building_id="CHEM_HALL", floor=3),
                hazard_type="HAZMAT"
            )
        ]
    )
    db.save_incident_state(state)

    res = client.post(f"/api/v1/incidents/{inc_id}/inject", json={
        "note": "Fire spreading to Stairwell B; secondary exit required."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "INJECT_PROCESSED"
    assert data["incident_id"] == inc_id

def test_incident_evaluation_and_audit_export():
    """Verify post-incident benchmark evaluation and FEMA audit export (SDD §7.1.4, FR-7.2)."""
    inc_id = "test_api_eval_inc"
    state = CampusEmergencyState(
        incident_id=inc_id,
        status="DISPATCHED",
        triage_assessment={"assessment": {"fema_classification": "HAZMAT_SPILL_CLASS_B", "threat_level": "CRITICAL", "containment_radius_meters": 150.0}},
        evacuation_routes={"routes": {"ROOM_301": ["ROOM_301", "CORRIDOR_3_WEST", "EXIT_WEST_GROUND"]}},
        resource_assignments={"staging_areas": {"incident_command_post": "Lot 4", "triage_tent_ccp": "South Field"}, "units_dispatched": [{"unit_id": "U1"}, {"unit_id": "U2"}, {"unit_id": "U3"}]},
        crisis_communications={"sms_broadcast": "CAMPUS EMERGENCY ALERT: Hazmat spill at Chem Hall. Evacuate via West exit. resq.edu", "pa_script": "ATTENTION. EVACUATE. I REPEAT: EVACUATE."},
        safety_audit_report={"citation_audit": {"ratio": 1.0, "violations": []}}
    )
    db.save_incident_state(state)

    # Evaluate
    res_eval = client.get(f"/api/v1/incidents/{inc_id}/evaluate?scenario_id=SCENARIO_ALPHA")
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert eval_data["pcm_score"] >= 0.90
    assert "breakdown" in eval_data

    # Export FEMA After-Action Report
    res_export = client.get(f"/api/v1/audit/{inc_id}/export")
    assert res_export.status_code == 200
    export_data = res_export.json()
    assert export_data["incident_id"] == inc_id
    assert "standard_compliance" in export_data

def test_list_incidents():
    """Verify listing all recorded incidents."""
    res = client.get("/api/v1/incidents")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

if __name__ == "__main__":
    test_health_and_readiness_probes()
    test_dashboard_root()
    test_incident_ingest_and_state()
    test_commander_credentials_and_signing()
    test_human_approval_and_gating()
    test_replan_feedback_loop()
    test_dynamic_event_injection()
    test_incident_evaluation_and_audit_export()
    test_list_incidents()
    print("ALL API ROUTE INTEGRATION TESTS PASSED!")
