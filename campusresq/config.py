"""
System Configuration for CampusResQ AI
Defines Latency budgets, API keys, fallback thresholds, and default paths.
"""

import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    # System Metadata
    app_name: str = "CampusResQ AI"
    version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Latency Budgets & Concurrency (SDD §9.3 & SRS §6.1)
    subagent_timeout_seconds: float = 4.0
    vector_search_latency_cap_ms: float = 300.0
    end_to_end_latency_cap_seconds: float = 15.0
    llm_timeout_fallback_seconds: float = 12.0
    max_concurrent_incidents: int = 5
    max_refinement_turns: int = 3
    
    # LLM Settings
    gemini_api_key: str = Field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    gemini_model: str = "gemini-1.5-flash"
    fallback_model: str = "deterministic-rule-engine"
    
    # Storage Paths
    db_path: str = "campusresq_state.db"
    vector_db_path: str = "campus_knowledge_base.json"
    audit_log_path: str = "audit_logs.jsonl"
    
    # Benchmark weights for Plan Completeness Metric (SDD §8.3 & SRS §7.1)
    pcm_weights: dict = {
        "hazard": 0.20,
        "evac": 0.25,
        "resource": 0.20,
        "comms": 0.20,
        "sop": 0.15
    }
    pcm_target_benchmark: float = 0.92
    hgcm_target_benchmark: float = 100.0

settings = Settings()
