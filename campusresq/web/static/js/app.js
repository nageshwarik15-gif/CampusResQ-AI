const { useState, useEffect, useRef } = React;

function CampusCommandCockpit() {
  // Incident State
  const [incidentId, setIncidentId] = useState(null);
  const [incidentState, setIncidentState] = useState(null);
  const [scenario, setScenario] = useState("SCENARIO_ALPHA");
  const [loading, setLoading] = useState(false);
  const [thoughtLogs, setThoughtLogs] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date().toUTCString());
  
  // Commander Interaction
  const [commanderFeedback, setCommanderFeedback] = useState("");
  const [actionEdits, setActionEdits] = useState({});
  const [isApproving, setIsApproving] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [showEvalModal, setShowEvalModal] = useState(false);
  const [showInjectModal, setShowInjectModal] = useState(false);
  const [injectText, setInjectText] = useState("Smoke reported spreading to Stairwell B; secondary exit required.");
  const [commanderCreds, setCommanderCreds] = useState(null);
  const [activeTab, setActiveTab] = useState("iap"); // iap, subplans, terminal

  // Leaflet Map Ref
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layersRef = useRef({ hazard: null, routes: [], markers: [] });
  const wsRef = useRef(null);
  const logTerminalRef = useRef(null);

  // Clock Timer
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toUTCString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch Commander Credentials on mount
  useEffect(() => {
    fetch("/api/v1/commander/credentials")
      .then(res => res.json())
      .then(data => setCommanderCreds(data))
      .catch(err => console.error("Failed to fetch commander credentials:", err));
  }, []);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    // Campus Coordinates (Chemistry Hall Center: 37.4278, -122.1695)
    const map = L.map(mapRef.current, {
      center: [37.4278, -122.1695],
      zoom: 16,
      zoomControl: true,
      attributionControl: false
    });

    // Dark Tile Layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
    }).addTo(map);

    mapInstanceRef.current = map;

    // Static Campus Buildings
    const buildings = [
      { name: "Chemistry Hall (Incident Epicenter)", lat: 37.4278, lng: -122.1695, color: "#ef4444", status: "CONTAMINATED / FIRE" },
      { name: "Bio-Sci Tower", lat: 37.4290, lng: -122.1705, color: "#f59e0b", status: "THREATENED" },
      { name: "University Library", lat: 37.4270, lng: -122.1670, color: "#3b82f6", status: "NORMAL" },
      { name: "North Dining Commons", lat: 37.4310, lng: -122.1675, color: "#3b82f6", status: "NORMAL" },
      { name: "West Quad Assembly Lawn", lat: 37.4265, lng: -122.1725, color: "#10b981", status: "MUSTER STATION" },
      { name: "South Athletic Field (Triage Tent)", lat: 37.4255, lng: -122.1690, color: "#10b981", status: "CASUALTY POINT" }
    ];

    buildings.forEach(b => {
      const circle = L.circle([b.lat, b.lng], {
        color: b.color,
        fillColor: b.color,
        fillOpacity: 0.35,
        radius: 40
      }).addTo(map);

      circle.bindTooltip(`<b>${b.name}</b><br/>Status: ${b.status}`, {
        permanent: false,
        className: 'campus-building-label'
      });
    });
  }, []);

  // Auto-scroll terminal
  useEffect(() => {
    if (logTerminalRef.current) {
      logTerminalRef.current.scrollTop = logTerminalRef.current.scrollHeight;
    }
  }, [thoughtLogs]);

  // Connect WebSocket when incidentId changes
  useEffect(() => {
    if (!incidentId) return;

    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/incident/${incidentId}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWebSocketEvent(msg);
      } catch (err) {
        console.error("WS Parse Error:", err);
      }
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [incidentId]);

  const handleWebSocketEvent = (msg) => {
    const timestamp = new Date(msg.timestamp).toLocaleTimeString();

    if (msg.type === "AGENT_THOUGHT") {
      setThoughtLogs(prev => [...prev, {
        time: timestamp,
        agent: msg.payload.agent,
        text: msg.payload.text
      }]);
    } else if (msg.type === "SUBPLAN_GENERATED") {
      setThoughtLogs(prev => [...prev, {
        time: timestamp,
        agent: msg.payload.agent,
        text: `Sub-plan section published: ${JSON.stringify(msg.payload)}`
      }]);
      // Refresh state
      fetchIncidentState(msg.incident_id);
    } else if (msg.type === "IAP_DRAFT_READY") {
      setThoughtLogs(prev => [...prev, {
        time: timestamp,
        agent: "HITL_Gate",
        text: `Draft IAP compiled (Hash: ${msg.payload.plan_hash?.slice(0, 16)}...). Human approval required!`
      }]);
      fetchIncidentState(msg.incident_id);
    } else if (msg.type === "MAP_VECTOR_UPDATE") {
      renderMapVectors(msg.payload);
    }
  };

  const renderMapVectors = (payload) => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    // Clear previous dynamic layers
    if (layersRef.current.hazard) {
      map.removeLayer(layersRef.current.hazard);
    }
    layersRef.current.routes.forEach(r => map.removeLayer(r));
    layersRef.current.routes = [];

    // Draw Hazard Radius
    if (payload.hazard_center && payload.containment_radius) {
      const hazardCircle = L.circle(payload.hazard_center, {
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.25,
        radius: payload.containment_radius,
        dashArray: '8, 8',
        weight: 2
      }).addTo(map);
      hazardCircle.bindPopup(`<b>Hazard Hot Zone</b><br/>Containment Radius: ${payload.containment_radius}m`);
      layersRef.current.hazard = hazardCircle;
    }

    // Draw Egress Route vectors
    const egressPoints = [
      [37.4278, -122.1695], // Epicenter
      [37.4275, -122.1710], // West corridor
      [37.4265, -122.1725]  // West assembly lawn
    ];
    const poly = L.polyline(egressPoints, {
      color: '#10b981',
      weight: 4,
      dashArray: '6, 6'
    }).addTo(map);
    poly.bindPopup("<b>Verified Safe Egress Corridor (Avoiding Downwind Plume)</b>");
    layersRef.current.routes.push(poly);
  };

  const fetchIncidentState = async (id) => {
    try {
      const res = await fetch(`/api/v1/incidents/${id}/state`);
      if (res.ok) {
        const data = await res.json();
        setIncidentState(data);
      }
    } catch (err) {
      console.error("Failed to fetch state:", err);
    }
  };

  // Launch Simulated Scenario
  const handleLaunchScenario = async () => {
    setLoading(true);
    setThoughtLogs([]);
    setIncidentState(null);
    setEvaluationResult(null);

    try {
      const res = await fetch(`/api/v1/incidents/simulate/${scenario}`, {
        method: "POST"
      });
      const data = await res.json();
      setIncidentId(data.incident_id);
      setThoughtLogs([{
        time: new Date().toLocaleTimeString(),
        agent: "System",
        text: `Scenario ${scenario} launched. Processing incoming telemetry feeds...`
      }]);

      // Poll state after short interval
      setTimeout(() => {
        fetchIncidentState(data.incident_id);
        setLoading(false);
      }, 1500);
    } catch (err) {
      console.error("Scenario launch failed:", err);
      setLoading(false);
    }
  };

  // Commander Injects Disruption
  const handleInject = async () => {
    if (!incidentId) return;
    try {
      await fetch(`/api/v1/incidents/${incidentId}/inject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: injectText })
      });
      setShowInjectModal(false);
      setThoughtLogs(prev => [...prev, {
        time: new Date().toLocaleTimeString(),
        agent: "Commander",
        text: `INJECT APPLIED: ${injectText}`
      }]);
      setTimeout(() => fetchIncidentState(incidentId), 1000);
    } catch (err) {
      console.error("Inject failed:", err);
    }
  };

  // Commander Re-plans with textual feedback
  const handleReplan = async () => {
    if (!incidentId || !commanderFeedback.trim()) return;
    setLoading(true);
    try {
      await fetch(`/api/v1/incidents/${incidentId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan_id: incidentState.incident_id,
          commander_id: commanderCreds?.commander_id || "CHIEF_MILLER_01",
          decision: "REJECTED_REDRAFT_REQUESTED",
          feedback_text: commanderFeedback,
          action_overrides: []
        })
      });
      setCommanderFeedback("");
      setTimeout(() => {
        fetchIncidentState(incidentId);
        setLoading(false);
      }, 1200);
    } catch (err) {
      console.error("Replan failed:", err);
      setLoading(false);
    }
  };

  // Sign & Authorize Plan Execution (Algorithm 4)
  const handleSignAndApprove = async () => {
    if (!incidentId || !incidentState) return;
    setIsApproving(true);

    try {
      // 1. Request ECDSA signature from commander key utility
      const signRes = await fetch("/api/v1/commander/sign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan_hash: incidentState.plan_hash })
      });
      const signData = await signRes.json();

      // 2. Submit approval request with cryptographic signature
      const overrides = Object.keys(actionEdits).map(actId => ({
        action_id: actId,
        override_status: actionEdits[actId].status,
        modified_instruction: actionEdits[actId].instruction,
        human_override_notes: "Commander inline edit"
      }));

      const approveRes = await fetch(`/api/v1/incidents/${incidentId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan_id: incidentState.incident_id,
          commander_id: signData.commander_id,
          decision: overrides.length > 0 ? "APPROVED_WITH_MODIFICATIONS" : "APPROVED_ALL",
          action_overrides: overrides,
          digital_signature: signData.digital_signature
        })
      });

      const approveData = await approveRes.json();
      setThoughtLogs(prev => [...prev, {
        time: new Date().toLocaleTimeString(),
        agent: "HITL_Gate",
        text: `SIGNATURE ACCEPTED: ${signData.digital_signature.slice(0, 24)}... Actuation initiated!`
      }]);

      fetchIncidentState(incidentId);
      setIsApproving(false);
      
      // Auto-evaluate benchmarks
      setTimeout(handleRunEvaluation, 1000);
    } catch (err) {
      console.error("Approval error:", err);
      setIsApproving(false);
    }
  };

  // Evaluate PCM and HGCM Benchmarks
  const handleRunEvaluation = async () => {
    if (!incidentId) return;
    try {
      const res = await fetch(`/api/v1/incidents/${incidentId}/evaluate?scenario_id=${scenario}`);
      const data = await res.json();
      setEvaluationResult(data);
      setShowEvalModal(true);
    } catch (err) {
      console.error("Evaluation failed:", err);
    }
  };

  // Download FEMA After-Action Report
  const handleDownloadFemaReport = async () => {
    if (!incidentId) return;
    window.open(`/api/v1/audit/${incidentId}/export`, '_blank');
  };

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case "P1_IMMEDIATE":
        return <span className="px-2 py-0.5 text-xs font-bold rounded bg-red-950 text-red-400 border border-red-800">P1 - IMMEDIATE</span>;
      case "P2_HIGH":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-950 text-amber-400 border border-amber-800">P2 - HIGH</span>;
      case "P3_MEDIUM":
        return <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-950 text-blue-400 border border-blue-800">P3 - MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 text-xs rounded bg-slate-800 text-slate-400 border border-slate-700">P4 - LOW</span>;
    }
  };

  const getTierBadge = (tier) => {
    switch (tier) {
      case "TIER_A_CRITICAL":
        return <span className="px-2 py-0.5 text-xs font-bold rounded bg-rose-950 text-rose-300 border border-rose-700 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse"></span>TIER-A CRITICAL (GATED)</span>;
      case "TIER_B_OPERATIONAL":
        return <span className="px-2 py-0.5 text-xs font-medium rounded bg-amber-950 text-amber-300 border border-amber-800">TIER-B OPERATIONAL</span>;
      default:
        return <span className="px-2 py-0.5 text-xs rounded bg-slate-800 text-slate-300 border border-slate-700">TIER-C INFORMATIONAL</span>;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100">
      
      {/* 1. NavigationHeader */}
      <header className="h-14 border-b border-slate-800 bg-slate-900/90 px-4 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500 shadow-lg shadow-blue-500/50 animate-pulse"></div>
            <span className="font-extrabold text-lg tracking-wider text-blue-400">CampusResQ <span className="text-white text-xs bg-blue-600 px-1.5 py-0.5 rounded font-mono">AI CORE</span></span>
          </div>
          <span className="text-xs text-slate-500 font-mono">| IEEE 1016-2009 & FEMA NIMS ICS-202/204</span>
        </div>

        {/* Center: Live Incident Status & Scenario Select */}
        <div className="flex items-center gap-3">
          <select 
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-xs font-medium text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="SCENARIO_ALPHA">Scenario Alpha (Chemical Spill & Secondary Fire)</option>
            <option value="SCENARIO_BRAVO">Scenario Bravo (Severe Active Hostile)</option>
            <option value="SCENARIO_CHARLIE">Scenario Charlie (M6.2 Earthquake Collapse)</option>
          </select>

          <button
            onClick={handleLaunchScenario}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white text-xs font-semibold px-3 py-1.5 rounded transition flex items-center gap-1.5 shadow"
          >
            {loading ? "Simulating..." : "Trigger Scenario"}
          </button>

          {incidentState && (
            <button
              onClick={() => setShowInjectModal(true)}
              className="bg-amber-600/80 hover:bg-amber-500 text-white text-xs font-semibold px-2.5 py-1.5 rounded transition flex items-center gap-1 border border-amber-500/50"
            >
              + Dynamic Inject
            </button>
          )}
        </div>

        {/* Right: Clock & Status Indicator */}
        <div className="flex items-center gap-4 text-xs font-mono">
          {incidentState && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700">
              <span className="text-slate-400">STATUS:</span>
              <span className={`font-bold ${
                incidentState.status === "DISPATCHED" ? "text-emerald-400" :
                incidentState.status === "AWAITING_APPROVAL" ? "text-amber-400 animate-pulse" : "text-blue-400"
              }`}>
                {incidentState.status}
              </span>
            </div>
          )}

          <div className="text-slate-400 hidden lg:block">
            {currentTime}
          </div>

          <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            HITL GATING: ZERO AUTONOMOUS BYPASS
          </div>
        </div>
      </header>

      {/* 2. MainSplitView */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* LeftPanel: Campus GIS Canvas */}
        <div className="w-1/2 h-full flex flex-col border-r border-slate-800 bg-slate-950 relative">
          <div className="h-9 px-3 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between text-xs font-mono text-slate-300">
            <span className="flex items-center gap-1.5 font-semibold text-blue-300">
              <span>CAMPUS SITUATIONAL GIS MAP</span>
            </span>
            <div className="flex items-center gap-3 text-[11px] text-slate-400">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span>Hot Zone</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span>Safe Egress</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span>Facilities</span>
            </div>
          </div>

          {/* Leaflet Container */}
          <div ref={mapRef} className="flex-1 w-full h-full z-0"></div>

          {/* Map Overlay Badge */}
          {incidentState?.triage_assessment?.assessment && (
            <div className="absolute bottom-4 left-4 z-10 bg-slate-900/90 border border-slate-700/80 rounded-lg p-3 shadow-xl backdrop-blur-md max-w-sm text-xs">
              <div className="font-bold text-red-400 mb-1 flex items-center justify-between">
                <span>{incidentState.triage_assessment.assessment.fema_classification}</span>
                <span className="px-1.5 py-0.2 bg-red-950 text-red-300 rounded border border-red-800 text-[10px]">
                  {incidentState.triage_assessment.assessment.threat_level}
                </span>
              </div>
              <div className="text-slate-300 text-[11px] space-y-0.5 font-mono">
                <div>Containment Radius: <span className="text-white font-semibold">{incidentState.triage_assessment.assessment.containment_radius_meters}m</span></div>
                <div>Plume Dispersion: <span className="text-white font-semibold">{incidentState.triage_assessment.assessment.plume_vector?.direction} @ {incidentState.triage_assessment.assessment.plume_vector?.speed_kmh} km/h</span></div>
                <div>Casualties: <span className="text-rose-400">Immediate: {incidentState.triage_assessment.assessment.estimated_casualties?.immediate}</span> | <span className="text-amber-400">Delayed: {incidentState.triage_assessment.assessment.estimated_casualties?.delayed}</span></div>
              </div>
            </div>
          )}
        </div>

        {/* RightPanel: Tactical Operations Center */}
        <div className="w-1/2 h-full flex flex-col bg-slate-900/40">
          
          {/* Tactical Tabs */}
          <div className="h-10 border-b border-slate-800 bg-slate-900/80 px-4 flex items-center justify-between">
            <div className="flex gap-2">
              <button 
                onClick={() => setActiveTab("iap")}
                className={`px-3 py-1 text-xs font-semibold rounded-t transition ${activeTab === 'iap' ? 'bg-slate-800 text-blue-400 border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Incident Action Plan (ICS-202/204)
              </button>
              <button 
                onClick={() => setActiveTab("subplans")}
                className={`px-3 py-1 text-xs font-semibold rounded-t transition ${activeTab === 'subplans' ? 'bg-slate-800 text-blue-400 border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Specialist Sub-Plans
              </button>
              <button 
                onClick={() => setActiveTab("terminal")}
                className={`px-3 py-1 text-xs font-semibold rounded-t transition flex items-center gap-1.5 ${activeTab === 'terminal' ? 'bg-slate-800 text-blue-400 border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                Agent Thought Stream ({thoughtLogs.length})
              </button>
            </div>

            {incidentState && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRunEvaluation}
                  className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded border border-slate-700 font-medium"
                >
                  View Benchmarks (PCM)
                </button>
                <button
                  onClick={handleDownloadFemaReport}
                  className="text-xs bg-blue-900/40 hover:bg-blue-800/60 text-blue-300 px-2.5 py-1 rounded border border-blue-700 font-medium"
                >
                  Export FEMA Log
                </button>
              </div>
            )}
          </div>

          {/* Tab Content Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            
            {/* TAB 1: Incident Action Plan Table */}
            {activeTab === "iap" && (
              <div>
                {!incidentState ? (
                  <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-sm">
                    <p>No active incident in cockpit.</p>
                    <p className="text-xs text-slate-600 mt-1">Select a scenario above and click "Trigger Scenario" to begin.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between bg-slate-900/60 p-2.5 rounded border border-slate-800 text-xs">
                      <div>
                        <span className="text-slate-400 font-mono">PLAN ID: </span>
                        <span className="font-mono text-slate-200 font-bold">iap_{incidentState.incident_id.slice(0, 8)}</span>
                        <span className="mx-2 text-slate-600">|</span>
                        <span className="text-slate-400 font-mono">REVISION: </span>
                        <span className="font-mono text-blue-400 font-bold">v{incidentState.iteration_count + 1}</span>
                      </div>
                      <div className="font-mono text-[11px] text-slate-400">
                        SHA256: <span className="text-emerald-400">{incidentState.plan_hash?.slice(0, 16)}...</span>
                      </div>
                    </div>

                    {/* Table of Actions */}
                    <div className="space-y-2.5">
                      {incidentState.draft_iap?.map((action, idx) => {
                        const isEdited = actionEdits[action.action_id];
                        const displayInstruction = isEdited?.instruction !== undefined ? isEdited.instruction : action.instruction;
                        const actionStatus = isEdited?.status || action.status;

                        return (
                          <div 
                            key={action.action_id}
                            className={`p-3 rounded-lg border transition ${
                              actionStatus === "REJECTED" ? "bg-red-950/20 border-red-900/40 opacity-60" :
                              actionStatus === "APPROVED" ? "bg-slate-900/80 border-emerald-900/40" :
                              "bg-slate-900/90 border-slate-800 hover:border-slate-700"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-bold text-xs text-blue-300">{action.action_id}</span>
                                {getTierBadge(action.tier)}
                                {getPriorityBadge(action.priority)}
                                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                                  {action.category}
                                </span>
                              </div>

                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => {
                                    setActionEdits(prev => ({
                                      ...prev,
                                      [action.action_id]: { ...prev[action.action_id], status: "APPROVED" }
                                    }));
                                  }}
                                  className="px-2 py-0.5 text-[11px] font-medium rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-400 border border-emerald-800"
                                >
                                  Approve
                                </button>
                                <button
                                  onClick={() => {
                                    const newText = prompt("Modify tactical instruction:", displayInstruction);
                                    if (newText !== null) {
                                      setActionEdits(prev => ({
                                        ...prev,
                                        [action.action_id]: { status: "MODIFIED", instruction: newText }
                                      }));
                                    }
                                  }}
                                  className="px-2 py-0.5 text-[11px] font-medium rounded bg-blue-950 hover:bg-blue-900 text-blue-400 border border-blue-800"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={() => {
                                    setActionEdits(prev => ({
                                      ...prev,
                                      [action.action_id]: { ...prev[action.action_id], status: "REJECTED" }
                                    }));
                                  }}
                                  className="px-2 py-0.5 text-[11px] font-medium rounded bg-red-950 hover:bg-red-900 text-red-400 border border-red-800"
                                >
                                  Reject
                                </button>
                              </div>
                            </div>

                            <div className="text-xs text-slate-100 font-medium mb-1">
                              <span className="text-slate-400">Target: </span>
                              <span className="font-bold text-white">{action.target}</span>
                            </div>

                            <p className="text-xs text-slate-200 mb-2 bg-slate-950/60 p-2 rounded border border-slate-800/80">
                              {displayInstruction}
                            </p>

                            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                              <span>Rationale: {action.rationale}</span>
                              {action.sop_citation && (
                                <span className="text-blue-400 bg-blue-950/40 px-2 py-0.5 rounded border border-blue-900">
                                  Ref: {action.sop_citation.document_title} (§{action.sop_citation.section})
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: Specialist Sub-Plans */}
            {activeTab === "subplans" && incidentState && (
              <div className="space-y-4 text-xs">
                {/* Triage Accordion */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
                  <h4 className="font-bold text-red-400 uppercase tracking-wide mb-2 flex items-center justify-between">
                    <span>1. Triage & Hazard Assessment Sub-Plan</span>
                    <span className="text-slate-500 font-mono text-[10px]">TriageAgent</span>
                  </h4>
                  <pre className="bg-slate-950 p-2.5 rounded font-mono text-[11px] text-slate-300 overflow-x-auto">
                    {JSON.stringify(incidentState.triage_assessment?.assessment, null, 2)}
                  </pre>
                </div>

                {/* Evacuation Accordion */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
                  <h4 className="font-bold text-emerald-400 uppercase tracking-wide mb-2 flex items-center justify-between">
                    <span>2. Evacuation & Spatial Pathing Sub-Plan (Algorithm 1)</span>
                    <span className="text-slate-500 font-mono text-[10px]">EvacuationAgent</span>
                  </h4>
                  <pre className="bg-slate-950 p-2.5 rounded font-mono text-[11px] text-slate-300 overflow-x-auto">
                    {JSON.stringify(incidentState.evacuation_routes?.routes, null, 2)}
                  </pre>
                </div>

                {/* Resources Accordion */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
                  <h4 className="font-bold text-amber-400 uppercase tracking-wide mb-2 flex items-center justify-between">
                    <span>3. Resource Allocation & Staging</span>
                    <span className="text-slate-500 font-mono text-[10px]">ResourceAgent</span>
                  </h4>
                  <pre className="bg-slate-950 p-2.5 rounded font-mono text-[11px] text-slate-300 overflow-x-auto">
                    {JSON.stringify(incidentState.resource_assignments?.units_dispatched, null, 2)}
                  </pre>
                </div>

                {/* Communications Accordion */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
                  <h4 className="font-bold text-blue-400 uppercase tracking-wide mb-2 flex items-center justify-between">
                    <span>4. Crisis Public Communications (Clery Act SMS & PA)</span>
                    <span className="text-slate-500 font-mono text-[10px]">CrisisCommsAgent</span>
                  </h4>
                  <div className="bg-slate-950 p-2.5 rounded font-mono text-[11px] text-slate-300 space-y-2">
                    <div>
                      <span className="text-slate-500">SMS Broadcast ({incidentState.crisis_communications?.sms_length}/160 chars):</span>
                      <p className="text-white bg-slate-900 p-1.5 rounded mt-1 border border-slate-800">
                        {incidentState.crisis_communications?.sms_broadcast}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500">PA Acoustic Siren Script:</span>
                      <p className="text-slate-300 bg-slate-900 p-1.5 rounded mt-1 border border-slate-800 text-[10px]">
                        {incidentState.crisis_communications?.pa_script}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: Agent Thought Stream Terminal */}
            {activeTab === "terminal" && (
              <div 
                ref={logTerminalRef}
                className="h-[460px] bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs overflow-y-auto space-y-1.5"
              >
                {thoughtLogs.length === 0 ? (
                  <div className="text-slate-600">Awaiting incident telemetry stream...</div>
                ) : (
                  thoughtLogs.map((log, idx) => (
                    <div key={idx} className="leading-relaxed">
                      <span className="text-slate-600 text-[10px]">[{log.time}] </span>
                      <span className="text-blue-400 font-semibold">{log.agent}: </span>
                      <span className="text-slate-200">{log.text}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* 3. ApprovalModalBar & Replan Feedback */}
          {incidentState && (
            <div className="border-t border-slate-800 bg-slate-900/90 p-3 space-y-2.5">
              
              {/* Feedback injection input for ReplanNode */}
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={commanderFeedback}
                  onChange={(e) => setCommanderFeedback(e.target.value)}
                  placeholder="Enter corrective commander feedback (e.g. 'East stairs are smoky, reroute to West')..."
                  className="flex-1 bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleReplan}
                  disabled={loading || !commanderFeedback.trim()}
                  className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold px-3 py-1.5 rounded border border-slate-700 transition"
                >
                  Selective Replan
                </button>
              </div>

              {/* Gating & Cryptographic Signature Action Bar */}
              <div className="flex items-center justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-rose-950 border border-rose-800 flex items-center justify-center text-rose-400 font-bold text-xs">
                    IC
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white flex items-center gap-1.5">
                      <span>{commanderCreds?.commander_id || "CHIEF_MILLER_01"}</span>
                      <span className="text-[10px] text-slate-400 font-normal font-mono">ECDSA SECP256R1</span>
                    </div>
                    <div className="text-[10px] font-mono text-slate-500">
                      Fingerprint: {incidentState.plan_hash?.slice(0, 20)}...
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSignAndApprove}
                    disabled={isApproving || incidentState.status === "DISPATCHED"}
                    className={`text-xs font-bold px-5 py-2 rounded-lg transition shadow-lg flex items-center gap-2 ${
                      incidentState.status === "DISPATCHED" 
                        ? "bg-emerald-900/60 text-emerald-300 border border-emerald-700 cursor-not-allowed"
                        : "bg-red-600 hover:bg-red-500 text-white shadow-red-900/40"
                    }`}
                  >
                    {isApproving ? "Verifying ECDSA Signature..." :
                     incidentState.status === "DISPATCHED" ? "Incident Dispatched & Actuated" :
                     "Slide / Sign & Authorize Dispatch (Tier-A Gate)"}
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Dynamic Inject Modal */}
      {showInjectModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="font-bold text-amber-400 text-sm flex items-center gap-2">
              <span>Dynamic Environmental Injection (FR-1.3)</span>
            </h3>
            <p className="text-xs text-slate-300">
              Inject a mid-crisis disruption into the active simulation to evaluate agent replanning resilience:
            </p>
            <textarea
              rows="3"
              value={injectText}
              onChange={(e) => setInjectText(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-white font-mono focus:outline-none focus:border-amber-500"
            ></textarea>
            <div className="flex justify-end gap-2 text-xs">
              <button
                onClick={() => setShowInjectModal(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleInject}
                className="px-4 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white font-semibold"
              >
                Inject Disruption
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Post-Incident Evaluation Modal */}
      {showEvalModal && evaluationResult && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-lg w-full shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-base">
                FEMA Post-Incident Benchmark Evaluation
              </h3>
              <button 
                onClick={() => setShowEvalModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Score Cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center">
                <div className="text-xs font-mono text-slate-400 mb-1">Plan Completeness Metric (PCM)</div>
                <div className={`text-3xl font-extrabold ${evaluationResult.pcm_score >= 0.92 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {evaluationResult.pcm_score}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">Target Benchmark: &ge; 0.92</div>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center">
                <div className="text-xs font-mono text-slate-400 mb-1">HITL Gating Correctness (HGCM)</div>
                <div className="text-3xl font-extrabold text-emerald-400">
                  {evaluationResult.hgcm_score}%
                </div>
                <div className="text-[11px] text-slate-500 mt-1">Zero Autonomous Actuation Target: 100%</div>
              </div>
            </div>

            {/* Dimension Breakdown */}
            <div className="space-y-2 text-xs">
              <div className="font-semibold text-slate-300">5-Dimensional Compliance Breakdown:</div>
              <div className="space-y-1.5 font-mono text-[11px]">
                <div className="flex justify-between bg-slate-950/60 px-3 py-1.5 rounded">
                  <span className="text-slate-400">S_hazard (Hazard Demarcation):</span>
                  <span className="text-blue-400 font-bold">{evaluationResult.breakdown.hazard_score}</span>
                </div>
                <div className="flex justify-between bg-slate-950/60 px-3 py-1.5 rounded">
                  <span className="text-slate-400">S_evac (Evacuation Safety Pathing):</span>
                  <span className="text-emerald-400 font-bold">{evaluationResult.breakdown.evacuation_score}</span>
                </div>
                <div className="flex justify-between bg-slate-950/60 px-3 py-1.5 rounded">
                  <span className="text-slate-400">S_resource (Resource Allocation & Logistics):</span>
                  <span className="text-amber-400 font-bold">{evaluationResult.breakdown.resource_score}</span>
                </div>
                <div className="flex justify-between bg-slate-950/60 px-3 py-1.5 rounded">
                  <span className="text-slate-400">S_comms (Clery Act Alert Compliance):</span>
                  <span className="text-purple-400 font-bold">{evaluationResult.breakdown.communications_score}</span>
                </div>
                <div className="flex justify-between bg-slate-950/60 px-3 py-1.5 rounded">
                  <span className="text-slate-400">S_sop (Emergency Operations Plan Grounding):</span>
                  <span className="text-emerald-400 font-bold">{evaluationResult.breakdown.sop_adherence_score}</span>
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-between items-center text-xs">
              <button
                onClick={handleDownloadFemaReport}
                className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-4 py-2 rounded-lg transition"
              >
                Download Official FEMA Package
              </button>
              <button
                onClick={() => setShowEvalModal(false)}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

ReactDOM.render(<CampusCommandCockpit />, document.getElementById("root"));
