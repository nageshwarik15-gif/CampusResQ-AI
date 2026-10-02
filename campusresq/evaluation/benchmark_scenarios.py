"""
Benchmark Emergency Scenarios Repository
Conforms strictly to SRS §7.4.
Provides gold-standard ground truth benchmarks for Scenarios Alpha, Bravo, and Charlie.
"""

from typing import Dict, Any

BENCHMARK_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "SCENARIO_ALPHA": {
        "scenario_id": "SCENARIO_ALPHA",
        "name": "Scenario Alpha: Chemical Spill & Secondary Fire",
        "building_id": "CHEM_HALL",
        "campus_zone": "SCIENCE_QUAD",
        "hazard_type": "HAZMAT_CHEMICAL_SPILL",
        "description": "Toxic spill in Chemistry Hall Room 302, fire alarm triggered, 45 occupants in building, chemical fumes spreading eastward.",
        "telemetry_payload": {
            "source_type": "iot_sensor",
            "location": {
                "campus_zone": "SCIENCE_QUAD",
                "building_id": "CHEM_HALL",
                "floor": 3,
                "room": "ROOM_302",
                "lat": 37.4278,
                "lng": -122.1695
            },
            "raw_data": {
                "hazard_indicators": ["FLAMMABLE_VAPOR_DETECTED", "FIRE_ALARM_PULL_STATION", "SMOKE_HIGH"],
                "sensor_metrics": {
                    "toxic_ppm": 145.0,
                    "temperature_c": 78.5,
                    "co_ppm": 42.0,
                    "occupants_count": 45
                },
                "transcript_text": "911 Dispatch: Multiple alarms in Chem Hall 3rd floor. Lab student reports solvent container dropped and ignited."
            }
        },
        "ground_truth": {
            "primary_hazard": "HAZMAT_SPILL_CLASS_B",
            "threat_level": "CRITICAL",
            "min_containment_radius_m": 150.0,
            "must_avoid_routes": ["STAIRWELL_EAST_3", "CORRIDOR_3_EAST", "ROOM_302"],
            "required_resources": ["ENGINE-4", "HAZMAT-1", "MED-1"],
            "required_staging": ["incident_command_post", "triage_tent_ccp"],
            "required_citations": ["Hazardous Material Incident Protocol", "Campus Evacuation & Life Safety Standard"]
        }
    },
    "SCENARIO_BRAVO": {
        "scenario_id": "SCENARIO_BRAVO",
        "name": "Scenario Bravo: Severe Active Threat / Active Hostile",
        "building_id": "NORTH_DINING",
        "campus_zone": "NORTH_COMMONS",
        "hazard_type": "ACTIVE_HOSTILE_ASSAULT",
        "description": "Multiple 911 calls reporting armed individual near North Dining Commons, injured casualties reported, panic in adjacent Library.",
        "telemetry_payload": {
            "source_type": "caller_transcript",
            "location": {
                "campus_zone": "NORTH_COMMONS",
                "building_id": "NORTH_DINING",
                "floor": 1,
                "room": "MAIN_DINING_HALL",
                "lat": 37.4310,
                "lng": -122.1675
            },
            "raw_data": {
                "hazard_indicators": ["ACOUSTIC_GUNSHOT_DETECTED", "PANIC_BUTTON_ENGAGED"],
                "sensor_metrics": {
                    "shots_detected": 4,
                    "estimated_hostiles": 1,
                    "occupants_count": 280
                },
                "transcript_text": "Caller from North Dining Commons: Shots fired near east entrance! Multiple people running into Library!"
            }
        },
        "ground_truth": {
            "primary_hazard": "ACTIVE_HOSTILE_ASSAULT",
            "threat_level": "CRITICAL",
            "min_containment_radius_m": 300.0,
            "must_avoid_routes": ["EAST_TERRACE_EXIT"],
            "required_resources": ["CAMPUS_POLICE_SWAT", "MED-1", "MED-2"],
            "required_staging": ["incident_command_post", "triage_tent_ccp"],
            "required_citations": ["Active Threat & Hostile Intruder Protocol", "Crisis Communications & Clery Act Emergency Notification"]
        }
    },
    "SCENARIO_CHARLIE": {
        "scenario_id": "SCENARIO_CHARLIE",
        "name": "Scenario Charlie: Mass Casualty Earthquake & Structural Collapse",
        "building_id": "DORM_VILLAGE",
        "campus_zone": "SOUTH_RESIDENTIAL",
        "hazard_type": "SEISMIC_STRUCTURAL_COLLAPSE",
        "description": "Structural damage in dormitories, power grid offline, cellular congestion, multiple trapped occupants requiring triage prioritization.",
        "telemetry_payload": {
            "source_type": "iot_sensor",
            "location": {
                "campus_zone": "SOUTH_RESIDENTIAL",
                "building_id": "DORM_VILLAGE",
                "floor": 2,
                "room": "BUILDING_C_CENTRAL",
                "lat": 37.4250,
                "lng": -122.1720
            },
            "raw_data": {
                "hazard_indicators": ["SEISMOMETER_MAGNITUDE_6_2", "GAS_LEAK_TRIGGER", "GRID_POWER_LOST"],
                "sensor_metrics": {
                    "peak_ground_accel": 0.45,
                    "structural_tilt_deg": 4.2,
                    "gas_flow_abnormal": True,
                    "occupants_count": 520
                },
                "transcript_text": "Emergency Facilities: Magnitude 6.2 seismic alert. Dorm C masonry collapse reported. Gas smell on south quad."
            }
        },
        "ground_truth": {
            "primary_hazard": "SEISMIC_STRUCTURAL_COLLAPSE",
            "threat_level": "CRITICAL",
            "min_containment_radius_m": 250.0,
            "must_avoid_routes": ["ELEVATORS", "BRICK_FACADE_WEST"],
            "required_resources": ["HEAVY_RESCUE-1", "SEARCH_DOG_TEAM", "MED-1", "MED-2"],
            "required_staging": ["incident_command_post", "triage_tent_ccp"],
            "required_citations": ["Major Seismic Event & Structural Collapse Response"]
        }
    }
}
