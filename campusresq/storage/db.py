"""
Persistent Relational Storage and Black-Box Audit Logger
Conforms strictly to IEEE 1016-2009 SDD §6.1, §6.2 and SRS §5.7.
Uses SQLite for structured entities and JSON-Lines for immutable FEMA black-box audit trails.
"""

import sqlite3
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from ..config import settings
from ..models.schemas import (
    CampusEmergencyState,
    TacticalAction,
    HumanApprovalRecord,
    DispatchAuditLog
)

class EmergencyDatabase:
    def __init__(self, db_file: str = "campusresq_state.db", audit_file: str = "audit_logs.jsonl"):
        self.db_file = db_file
        self.audit_file = audit_file
        self._init_sqlite()
        
    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        # 1. Incidents Table
        c.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            started_at TEXT,
            ended_at TEXT,
            status TEXT,
            primary_hazard TEXT,
            initial_location TEXT,
            state_json TEXT
        )
        ''')
        
        # 2. Incident Action Plans
        c.execute('''
        CREATE TABLE IF NOT EXISTS incident_action_plans (
            plan_id TEXT PRIMARY KEY,
            incident_id TEXT,
            version INTEGER,
            generated_at TEXT,
            confidence_score REAL,
            completeness_score REAL,
            plan_status TEXT,
            plan_hash TEXT,
            FOREIGN KEY (incident_id) REFERENCES incidents (incident_id)
        )
        ''')
        
        # 3. Tactical Actions
        c.execute('''
        CREATE TABLE IF NOT EXISTS tactical_actions (
            action_id TEXT PRIMARY KEY,
            plan_id TEXT,
            tier TEXT,
            priority TEXT,
            category TEXT,
            target TEXT,
            instruction TEXT,
            rationale TEXT,
            sop_citation_json TEXT,
            line_status TEXT,
            override_notes TEXT
        )
        ''')
        
        # 4. Human Approval Records
        c.execute('''
        CREATE TABLE IF NOT EXISTS human_approval_records (
            approval_id TEXT PRIMARY KEY,
            plan_id TEXT,
            commander_id TEXT,
            signed_at TEXT,
            decision_type TEXT,
            modification_summary TEXT,
            cryptographic_signature TEXT
        )
        ''')
        
        # 5. Dispatch Audit Logs
        c.execute('''
        CREATE TABLE IF NOT EXISTS dispatch_audit_logs (
            log_id TEXT PRIMARY KEY,
            action_id TEXT,
            plan_id TEXT,
            dispatched_at TEXT,
            destination_channel TEXT,
            delivery_status TEXT,
            response_ack_json TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    def save_incident_state(self, state: CampusEmergencyState):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        hazard = "UNKNOWN"
        loc = "CAMPUS"
        if state.current_telemetry:
            hazard = state.current_telemetry[-1].hazard_type
            loc = state.current_telemetry[-1].location.building_id
            
        c.execute('''
        INSERT INTO incidents (incident_id, started_at, status, primary_hazard, initial_location, state_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(incident_id) DO UPDATE SET
            status = excluded.status,
            state_json = excluded.state_json
        ''', (state.incident_id, now, state.status, hazard, loc, state.model_dump_json()))
        
        # Record tactical actions
        plan_id = f"plan_{state.incident_id[:8]}"
        for act in state.draft_iap:
            c.execute('''
            INSERT INTO tactical_actions 
            (action_id, plan_id, tier, priority, category, target, instruction, rationale, sop_citation_json, line_status, override_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(action_id) DO UPDATE SET
                line_status = excluded.line_status,
                instruction = excluded.instruction,
                override_notes = excluded.override_notes
            ''', (
                act.action_id,
                plan_id,
                act.tier,
                act.priority,
                act.category,
                act.target,
                act.instruction,
                act.rationale,
                json.dumps(act.sop_citation),
                act.status,
                act.override_notes
            ))
            
        conn.commit()
        conn.close()
        
        # Record in Black-box JSON lines log (SRS §5.7)
        self.append_black_box_log({
            "event_type": "STATE_UPDATE",
            "timestamp": now,
            "incident_id": state.incident_id,
            "status": state.status,
            "plan_hash": state.plan_hash,
            "draft_action_count": len(state.draft_iap)
        })

    def get_incident_state(self, incident_id: str) -> Optional[CampusEmergencyState]:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT state_json FROM incidents WHERE incident_id = ?", (incident_id,))
        row = c.fetchone()
        conn.close()
        
        if row and row[0]:
            data = json.loads(row[0])
            return CampusEmergencyState(**data)
        return None

    def list_incidents(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT incident_id, started_at, status, primary_hazard, initial_location FROM incidents ORDER BY started_at DESC")
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "incident_id": r[0],
                "started_at": r[1],
                "status": r[2],
                "primary_hazard": r[3],
                "initial_location": r[4]
            }
            for r in rows
        ]

    def record_approval(self, record: HumanApprovalRecord):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''
        INSERT INTO human_approval_records
        (approval_id, plan_id, commander_id, signed_at, decision_type, modification_summary, cryptographic_signature)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.approval_id,
            record.plan_id,
            record.commander_id,
            record.timestamp,
            record.decision,
            json.dumps(record.modifications),
            record.digital_signature
        ))
        conn.commit()
        conn.close()
        
        self.append_black_box_log({
            "event_type": "HUMAN_APPROVAL_RECORDED",
            "timestamp": record.timestamp,
            "approval_id": record.approval_id,
            "plan_id": record.plan_id,
            "commander_id": record.commander_id,
            "decision": record.decision,
            "cryptographic_signature": record.digital_signature
        })

    def record_dispatch_logs(self, logs: List[DispatchAuditLog]):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        for l in logs:
            c.execute('''
            INSERT INTO dispatch_audit_logs
            (log_id, action_id, plan_id, dispatched_at, destination_channel, delivery_status, response_ack_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                l.log_id,
                l.action_id,
                l.plan_id,
                l.dispatched_at,
                l.destination_channel,
                l.delivery_status,
                json.dumps(l.response_ack)
            ))
            self.append_black_box_log({
                "event_type": "ACTUATOR_DISPATCH",
                "timestamp": l.dispatched_at,
                "action_id": l.action_id,
                "channel": l.destination_channel,
                "ack": l.response_ack
            })
        conn.commit()
        conn.close()

    def append_black_box_log(self, record: Dict[str, Any]):
        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def export_after_action_report(self, incident_id: str) -> Dict[str, Any]:
        """
        Exports full after-action FEMA package containing state, telemetry, logs, signatures, and evaluations.
        """
        state = self.get_incident_state(incident_id)
        logs = []
        if os.path.exists(self.audit_file):
            with open(self.audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line.strip())
                        if obj.get("incident_id") == incident_id or incident_id in str(obj):
                            logs.append(obj)
                    except:
                        pass
                        
        return {
            "incident_id": incident_id,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "standard_compliance": "FEMA NIMS ICS-202/204 / IEEE 1016-2009",
            "state": state.model_dump() if state else None,
            "audit_trail_events": logs
        }

db = EmergencyDatabase()
