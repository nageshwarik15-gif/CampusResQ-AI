"""
Real-Time Event Bus for Streaming Agent Thoughts and Map Updates
Conforms to SDD §6.4 and §7.2.
"""

from typing import Dict, List, Any
import json
from datetime import datetime, timezone

class EventBus:
    def __init__(self):
        self.active_connections: Dict[str, List[Any]] = {}
        self.global_listeners: List[Any] = []

    async def connect(self, websocket: Any, incident_id: str):
        await websocket.accept()
        if incident_id not in self.active_connections:
            self.active_connections[incident_id] = []
        self.active_connections[incident_id].append(websocket)

    def disconnect(self, websocket: Any, incident_id: str):
        if incident_id in self.active_connections:
            if websocket in self.active_connections[incident_id]:
                self.active_connections[incident_id].remove(websocket)

    async def broadcast_event(self, incident_id: str, event_type: str, data: Any):
        payload = {
            "type": event_type,
            "incident_id": incident_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": data
        }
        raw_msg = json.dumps(payload)
        
        # Broadcast to incident room
        conns = list(self.active_connections.get(incident_id, []))
        for ws in conns:
            try:
                await ws.send_text(raw_msg)
            except Exception:
                self.disconnect(ws, incident_id)
                
        # Broadcast to global listeners
        for ws in list(self.global_listeners):
            try:
                await ws.send_text(raw_msg)
            except Exception:
                if ws in self.global_listeners:
                    self.global_listeners.remove(ws)

event_bus = EventBus()
