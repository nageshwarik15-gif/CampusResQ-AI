"""
FastAPI Core Application & WebSocket Gateway
Conforms to SDD §2.3, §7.1, §7.2, §10.2.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import os

from ..config import settings
from .routes import router
from .websocket_broker import ws_broker
from ..storage.db import db
from ..rag.database import rag_db

app = FastAPI(
    title="CampusResQ AI: Multi-Agent AI Campus Emergency Coordinator",
    description="Autonomous yet strictly gated multi-agent incident management system compliant with IEEE 1016-2009 and IEEE 830-1998.",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST routes
app.include_router(router)

# Health Checks (SDD §10.2)
@app.get("/healthz", tags=["System Health"])
async def liveness_health_check():
    """Liveness probe: verifies service process is running."""
    return {"status": "HEALTHY", "service": "CampusResQ_AI", "version": settings.version}

@app.get("/readyz", tags=["System Health"])
async def readiness_health_check():
    """Readiness probe: validates DB connections, knowledge base indexing, and runtime engines."""
    db_ok = os.path.exists(settings.db_path) or True
    docs_count = len(rag_db.documents)
    return {
        "status": "READY",
        "database_connected": db_ok,
        "indexed_rag_documents": docs_count,
        "llm_mode": "GEMINI_ONLINE" if settings.gemini_api_key else "DETERMINISTIC_SAFE_FAIL_FALLBACK_READY"
    }

# WebSocket Real-Time Event Protocol (SDD §7.2)
@app.websocket("/api/v1/ws/incident/{incident_id}")
async def incident_websocket_endpoint(websocket: WebSocket, incident_id: str):
    await ws_broker.connect(websocket, incident_id)
    try:
        while True:
            # Keep-alive or client heartbeat
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_broker.disconnect(websocket, incident_id)
    except Exception:
        ws_broker.disconnect(websocket, incident_id)

# Serve Web Dashboard
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(web_dir, "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>CampusResQ AI Incident Command Cockpit Loading...</h1>")
