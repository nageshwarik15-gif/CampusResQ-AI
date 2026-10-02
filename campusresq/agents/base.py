"""
Base Specialist Agent Class
Conforms to SDD §3.3, §9.3 and SRS §6.5 (NFR-5.1 Pluggable Agents).
"""

from typing import Dict, Any, Optional
import time
import os
import json
from ..config import settings
from ..models.schemas import CampusEmergencyState

class BaseEmergencyAgent:
    """
    Abstract Base Class for all CampusResQ AI specialist agents.
    Provides uniform execution, timing, telemetry logging, and deterministic fallback support.
    """
    def __init__(self, agent_name: str, role: str):
        self.agent_name = agent_name
        self.role = role
        self.timeout = settings.subagent_timeout_seconds
        self.api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        
    async def run(self, state: CampusEmergencyState) -> Dict[str, Any]:
        """
        Executes the agent's domain deliberation with latency budget tracking and fallback.
        """
        start_time = time.perf_counter()
        thought_log = []
        
        try:
            thought_log.append(f"[{self.agent_name}] Initializing analysis for incident {state.incident_id}...")
            
            # If an API key is available, we could attempt Gemini SDK, otherwise or on timeout,
            # execute the deterministic specialized domain engine.
            result = await self.deliberate(state, thought_log)
            
            elapsed = time.perf_counter() - start_time
            thought_log.append(f"[{self.agent_name}] Deliberation completed in {elapsed:.3f}s.")
            result["thought_trace"] = thought_log
            result["execution_duration_ms"] = round(elapsed * 1000.0, 2)
            return result
            
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            thought_log.append(f"[{self.agent_name}] Encountered error: {str(e)}. Triggering deterministic fallback.")
            fallback_res = self.fallback_rule_engine(state)
            fallback_res["thought_trace"] = thought_log
            fallback_res["execution_duration_ms"] = round(elapsed * 1000.0, 2)
            fallback_res["fallback_active"] = True
            return fallback_res

    async def deliberate(self, state: CampusEmergencyState, thought_log: list) -> Dict[str, Any]:
        """Subclasses must implement domain logic."""
        raise NotImplementedError

    def fallback_rule_engine(self, state: CampusEmergencyState) -> Dict[str, Any]:
        """Subclasses must provide static deterministic backup logic."""
        raise NotImplementedError
