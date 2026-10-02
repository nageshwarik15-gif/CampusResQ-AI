"""
Server Runner for CampusResQ AI
Starts FastAPI server on port 8000.
"""

import uvicorn
import os
import sys

def main():
    print("=" * 70)
    print("  CAMPUSRESQ AI: MULTI-AGENT AI CAMPUS EMERGENCY COORDINATOR")
    print("  Compliant with IEEE Std 1016-2009 (SDD) & IEEE Std 830-1998 (SRS)")
    print("=" * 70)
    print("  - Web Dashboard:     http://localhost:8000/")
    print("  - API Documentation: http://localhost:8000/docs")
    print("  - OpenAPI Schema:    http://localhost:8000/openapi.json")
    print("  - Health Check:      http://localhost:8000/healthz")
    print("  - Readiness Probe:   http://localhost:8000/readyz")
    print("  - WebSocket Stream:  ws://localhost:8000/api/v1/ws/incident/{id}")
    print("=" * 70)
    
    uvicorn.run("campusresq.api.app:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
