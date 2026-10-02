"""
Dispatch & Actuator Service
Manages simulated physical actuators for campus emergency response.
Conforms to SDD §2.1, §2.2 and SRS §5.6.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
import uuid
from ..models.schemas import TacticalAction, DispatchAuditLog

class ActuatorEndpointManager:
    """
    Simulates physical and telecommunication emergency dispatch interfaces.
    """
    def __init__(self):
        self.dispatched_logs: List[DispatchAuditLog] = []
        self.active_lockdowns: List[str] = []
        self.broadcast_messages: List[Dict[str, Any]] = []

    def dispatch_action(self, action: TacticalAction, plan_id: str = "") -> DispatchAuditLog:
        now = datetime.now(timezone.utc).isoformat()
        category = action.category.upper()
        target = action.target
        instruction = action.instruction
        
        # Route to appropriate simulated actuator endpoint
        if category == "PUBLIC_ALERT":
            channel = "SMS_GATEWAY_TWILIO"
            receipt = {
                "service": "Twilio_Mock_SMS",
                "recipients_notified": 14250,
                "delivery_rate": "99.8%",
                "carrier_ack": "ACCEPTED_BY_TELCO",
                "text_transmitted": instruction[:160]
            }
            self.broadcast_messages.append({"channel": "SMS", "time": now, "content": instruction})
            
        elif category == "EVACUATION":
            channel = "CAMPUS_PA_SIREN"
            receipt = {
                "service": "Campus_Acoustic_PA",
                "speakers_active": 48,
                "siren_decibels": 115,
                "audio_loop_status": "BROADCASTING_REPEATING_TWICE",
                "zones": [target]
            }
            self.broadcast_messages.append({"channel": "PA_AUDIO", "time": now, "content": instruction})
            
        elif category == "LOCKDOWN":
            channel = "BUILDING_ACCESS_RELAY"
            receipt = {
                "service": "HID_Aero_Access_Controller",
                "relays_tripped": 32,
                "doors_locked": "MAGNETIC_FAIL_SECURE",
                "ingress_status": "BLOCKED",
                "egress_status": "PANIC_BAR_FREE_EXIT"
            }
            self.active_lockdowns.append(target)
            
        elif category in ("MEDICAL", "HAZMAT"):
            channel = "FIRST_RESPONDER_MDT"
            receipt = {
                "service": "Motorola_PremierOne_CAD",
                "units_notified": ["MED-1", "MED-2", "HAZMAT-1", "ENGINE-4"],
                "routing_waypoints_uploaded": True,
                "gps_ack_received": True
            }
        else:
            channel = "TACTICAL_DISPATCH_CONSOLE"
            receipt = {
                "service": "EOC_Console",
                "status": "LOGGED_AND_ACKNOWLEDGED"
            }

        log_entry = DispatchAuditLog(
            log_id=f"log_{uuid.uuid4().hex[:8]}",
            action_id=action.action_id,
            plan_id=plan_id,
            dispatched_at=now,
            destination_channel=channel,
            delivery_status="DELIVERED",
            response_ack=receipt
        )
        self.dispatched_logs.append(log_entry)
        return log_entry

    def dispatch_approved_plan(self, actions: List[TacticalAction], plan_id: str = "") -> List[DispatchAuditLog]:
        logs = []
        for act in actions:
            if act.status in ("APPROVED", "MODIFIED", "PENDING_APPROVAL"):
                log = self.dispatch_action(act, plan_id)
                logs.append(log)
        return logs

actuator_mgr = ActuatorEndpointManager()
