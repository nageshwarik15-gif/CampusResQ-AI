"""
Data Schemas for CampusResQ AI
Strictly conforms to IEEE 1016-2009 SDD §3.2, §5.3, §6.1, §7.1 and SRS §8.1, §8.2, §8.3.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()

class LocationCoordinates(BaseModel):
    lat: float
    lng: float

class LocationModel(BaseModel):
    campus_zone: str = "CENTRAL_CAMPUS"
    building_id: str
    floor: int = 1
    room: Optional[str] = None
    lat: float = 37.4275
    lng: float = -122.1697

class TelemetryEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=current_iso_time)
    source: str
    location: LocationModel
    hazard_type: str
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

class IncidentTelemetryPayload(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=current_iso_time)
    source_type: str = "iot_sensor"  # iot_sensor, caller_transcript, security_officer, video_analytic
    location: LocationModel
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class SOPCitation(BaseModel):
    document_title: str
    section: str
    page: int

class TacticalAction(BaseModel):
    action_id: str = Field(default_factory=lambda: f"ACT_{uuid.uuid4().hex[:6].upper()}")
    tier: str  # TIER_A_CRITICAL, TIER_B_OPERATIONAL, TIER_C_INFORMATIONAL
    priority: str  # P1_IMMEDIATE, P2_HIGH, P3_MEDIUM, P4_LOW
    category: str  # EVACUATION, LOCKDOWN, MEDICAL, HAZMAT, PUBLIC_ALERT
    target: str
    instruction: str
    rationale: str
    sop_citation: Dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, APPROVED, MODIFIED, REJECTED
    override_notes: Optional[str] = None

class IncidentClassification(BaseModel):
    primary_type: str
    severity_level: str  # LOW, MODERATE, SEVERE, CRITICAL
    affected_perimeter_meters: float

class IncidentActionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str
    version: int = 1
    generated_at: str = Field(default_factory=current_iso_time)
    status: str = "draft_pending_review"  # draft_pending_review, approved, modified, rejected
    confidence_score: float = 0.95
    incident_classification: Optional[IncidentClassification] = None
    tactical_actions: List[TacticalAction] = Field(default_factory=list)

class CampusEmergencyState(BaseModel):
    incident_id: str
    status: str = "ACTIVE"  # ACTIVE, AWAITING_APPROVAL, DISPATCHED, TERMINATED
    current_telemetry: List[TelemetryEvent] = Field(default_factory=list)
    rag_context: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Sub-agent outputs
    triage_assessment: Optional[Dict[str, Any]] = None
    evacuation_routes: Optional[Dict[str, Any]] = None
    resource_assignments: Optional[Dict[str, Any]] = None
    crisis_communications: Optional[Dict[str, Any]] = None
    safety_audit_report: Optional[Dict[str, Any]] = None
    
    # Consolidated Incident Action Plan
    draft_iap: List[TacticalAction] = Field(default_factory=list)
    approved_iap: List[TacticalAction] = Field(default_factory=list)
    
    # Human-In-The-Loop tracking
    commander_feedback: Optional[str] = None
    approval_signature: Optional[str] = None
    iteration_count: int = 0
    plan_hash: Optional[str] = None

class ActionOverride(BaseModel):
    action_id: str
    override_status: str = "MODIFIED"  # ACCEPTED, MODIFIED, DELETED
    modified_instruction: Optional[str] = None
    human_override_notes: Optional[str] = None

class ApprovalRequest(BaseModel):
    plan_id: str
    commander_id: str = "CHIEF_MILLER_01"
    decision: str = "APPROVED_ALL"  # APPROVED_ALL, APPROVED_WITH_MODIFICATIONS, REJECTED_REDRAFT_REQUESTED
    action_overrides: List[ActionOverride] = Field(default_factory=list)
    digital_signature: Optional[str] = None
    feedback_text: Optional[str] = None

class HumanApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    commander_id: str
    timestamp: str = Field(default_factory=current_iso_time)
    decision: str
    modifications: List[Dict[str, Any]] = Field(default_factory=list)
    digital_signature: str

class DispatchAuditLog(BaseModel):
    log_id: str = Field(default_factory=lambda: f"log_{uuid.uuid4().hex[:8]}")
    action_id: str
    plan_id: Optional[str] = None
    dispatched_at: str = Field(default_factory=current_iso_time)
    destination_channel: str
    delivery_status: str = "DELIVERED"
    response_ack: Dict[str, Any] = Field(default_factory=dict)

class EvaluationBreakdown(BaseModel):
    hazard_score: float
    evacuation_score: float
    resource_score: float
    communications_score: float
    sop_adherence_score: float

class EvaluationResult(BaseModel):
    incident_id: str
    pcm_score: float
    hgcm_score: float
    breakdown: EvaluationBreakdown
