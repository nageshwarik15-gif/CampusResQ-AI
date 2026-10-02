"""
Campus Knowledge Base Repository
Contains Emergency Operations Plan (EOP), Safety Data Sheets (SDS),
and Building Blueprint Spatial Metadata.
Conforms to SDD §4.1, §4.2 and SRS §3.3.
"""

from typing import List, Dict, Any

CAMPUS_KNOWLEDGE_DOCS: List[Dict[str, Any]] = [
    {
        "id": "eop_ch4_fire_sec3",
        "document_type": "EMERGENCY_SOP",
        "title": "Hazardous Material Incident Protocol",
        "applicable_buildings": ["CHEM_HALL", "BIO_SCI_TOWER", "ALL"],
        "hazard_categories": ["HAZMAT", "FIRE"],
        "section_id": "4.3.2",
        "page_number": 87,
        "content_text": (
            "In the event of an uncontrolled Class B flammable solvent spill exceeding 5 liters in Chemistry Hall, "
            "immediate evacuation of all floors above the incident is mandatory. Elevators must be recalled to Ground Floor "
            "and locked. Deploy dry chemical foam units. Do not introduce water streams directly into volatile organic vapor pool. "
            "Establish a minimum 150-meter perimeter cordon around the affected wing."
        ),
        "keywords": ["chemical", "spill", "solvent", "flammable", "chemistry", "hall", "fire", "elevators", "evacuate"]
    },
    {
        "id": "eop_ch2_evac_sec1",
        "document_type": "EMERGENCY_SOP",
        "title": "Campus Evacuation & Life Safety Standard",
        "applicable_buildings": ["ALL"],
        "hazard_categories": ["FIRE", "ACTIVE_THREAT", "HAZMAT", "EARTHQUAKE"],
        "section_id": "2.1.4",
        "page_number": 34,
        "content_text": (
            "All building occupants must proceed immediately down designated stairwells to primary ground floor exits. "
            "Elevators are mechanically disabled automatically upon fire alarm activation to prevent entrapment. "
            "In high-density incidents, evacuate the fire floor first, followed by the floor immediately above, then upper floors. "
            "Designate primary muster assembly points at least 100 meters away from building structural facades."
        ),
        "keywords": ["evacuation", "stairwell", "elevators", "disabled", "assembly", "muster", "exits"]
    },
    {
        "id": "eop_ch5_active_threat_sec2",
        "document_type": "EMERGENCY_SOP",
        "title": "Active Threat & Hostile Intruder Protocol",
        "applicable_buildings": ["ALL", "NORTH_DINING", "LIBRARY"],
        "hazard_categories": ["ACTIVE_THREAT"],
        "section_id": "5.2.1",
        "page_number": 112,
        "content_text": (
            "Upon notification of an active threat or armed hostile individual: Immediate RUN, HIDE, FIGHT procedure is initiated. "
            "Execute automated electronic magnetic door lockdowns for all adjacent buildings within 300 meters. "
            "Deploy Campus Police tactical intervention units immediately to isolate the threat. "
            "Establish unified incident command post at South Perimeter Staging lot. Notify regional SWAT and EMS casualty collection point."
        ),
        "keywords": ["active", "threat", "shooter", "armed", "lockdown", "police", "swat", "dining", "library"]
    },
    {
        "id": "eop_ch6_earthquake_sec1",
        "document_type": "EMERGENCY_SOP",
        "title": "Major Seismic Event & Structural Collapse Response",
        "applicable_buildings": ["ALL", "DORM_VILLAGE", "SCIENCE_CENTER"],
        "hazard_categories": ["EARTHQUAKE", "STRUCTURAL_COLLAPSE"],
        "section_id": "6.1.1",
        "page_number": 145,
        "content_text": (
            "Following seismic disturbance exceeding M5.5: Immediate DROP, COVER, HOLD ON. Post-shake, initiate orderly evacuation "
            "avoiding brick facades and exterior glass canopies. Facilities engineering must immediately shut down natural gas main valves "
            "and secondary electrical substations to prevent catastrophic gas explosion. Establish Search & Rescue triage grids in residence halls."
        ),
        "keywords": ["earthquake", "seismic", "structural", "collapse", "gas", "shutoff", "dorms", "triage"]
    },
    {
        "id": "eop_ch3_comms_clery",
        "document_type": "EMERGENCY_SOP",
        "title": "Crisis Communications & Clery Act Emergency Notification",
        "applicable_buildings": ["ALL"],
        "hazard_categories": ["FIRE", "ACTIVE_THREAT", "HAZMAT", "PUBLIC_ALERT"],
        "section_id": "3.4.1",
        "page_number": 58,
        "content_text": (
            "Under the federal Jeanne Clery Disclosure of Campus Security Policy and Campus Crime Statistics Act, an immediate "
            "Emergency Notification must be issued to the campus community upon confirmation of a significant emergency or dangerous situation. "
            "Broadcast SMS must be strictly under 160 characters, begin with 'CAMPUS EMERGENCY ALERT:', state location, hazard type, "
            "provide explicit imperative protective actions, and avoid unconfirmed victim speculation or tactical police operational details."
        ),
        "keywords": ["clery", "sms", "alert", "broadcast", "communications", "pa", "siren", "warning"]
    },
    {
        "id": "sds_hexane_solvent",
        "document_type": "SAFETY_DATA_SHEET",
        "title": "SDS #CHEM-041: n-Hexane Analytical Grade",
        "applicable_buildings": ["CHEM_HALL"],
        "hazard_categories": ["HAZMAT", "FIRE"],
        "section_id": "SDS-8.2",
        "page_number": 4,
        "content_text": (
            "CAS # 110-54-3. Highly flammable liquid and vapor (Flash point -22°C). Inhalation toxicity causes central nervous system "
            "depression and peripheral neuropathy. Combustion generates carbon monoxide and dense black smoke. Safe evacuation standoff "
            "distance: 100 meters minimum, 300 meters downwind in open air. First responders require Level B SCBA hazmat gear and vapor-suppressing foam."
        ),
        "keywords": ["sds", "hexane", "solvent", "flammable", "toxic", "cas", "110-54-3", "standoff", "scba"]
    },
    {
        "id": "sds_chlorine_gas",
        "document_type": "SAFETY_DATA_SHEET",
        "title": "SDS #CHEM-089: Compressed Chlorine Gas",
        "applicable_buildings": ["CHEM_HALL", "SCIENCE_CENTER"],
        "hazard_categories": ["HAZMAT"],
        "section_id": "SDS-6.1",
        "page_number": 2,
        "content_text": (
            "CAS # 7782-50-5. Fatal if inhaled. Corrosive oxidizer; reacts violently with water. Heavier than air; settles in low areas, "
            "basements, and ground-level storm drains. Evacuate 500 meters downwind immediately. Level A fully encapsulated gas-tight "
            "chemical protective suit mandatory for any entry into hot zone."
        ),
        "keywords": ["chlorine", "gas", "toxic", "cas", "7782-50-5", "level a", "suit", "downwind"]
    },
    {
        "id": "blueprint_chem_hall",
        "document_type": "SPATIAL_BLUEPRINT",
        "title": "Chemistry Hall Spatial Registry & Safety Equipment",
        "applicable_buildings": ["CHEM_HALL"],
        "hazard_categories": ["HAZMAT", "FIRE", "EVACUATION"],
        "section_id": "SP-101",
        "page_number": 12,
        "content_text": (
            "Chemistry Hall: 3 stories plus mechanical penthouse. Maximum occupancy: 420 persons. Emergency eyewash and chemical deluge showers "
            "located in Rooms 301, 302, 304, 201, 202. Class BC and Class ABC dry chemical fire extinguishers located adjacent to East and West "
            "stairwell doors on all floors. Main electrical breaker switch in Room 101-B. Heavy fire door auto-closures at floor dividers."
        ),
        "keywords": ["chemistry", "hall", "blueprint", "eyewash", "extinguishers", "stairwell", "exits", "occupancy"]
    },
    {
        "id": "blueprint_north_dining",
        "document_type": "SPATIAL_BLUEPRINT",
        "title": "North Dining Commons & Library Quad Layout",
        "applicable_buildings": ["NORTH_DINING", "LIBRARY"],
        "hazard_categories": ["ACTIVE_THREAT", "EVACUATION"],
        "section_id": "SP-204",
        "page_number": 18,
        "content_text": (
            "North Dining Commons: 2 main dining halls, kitchen loading bay, East terrace exit, West quad promenade exit. "
            "Occupancy during peak meal hours: 650 persons. Automatic electromagnetic door lock controls can be triggered from Central "
            "Security Console or Building Admin Panel Room 105. Connects via pedestrian skybridge to University Library West Wing."
        ),
        "keywords": ["dining", "commons", "library", "lockdown", "doors", "quad", "skybridge"]
    }
]
