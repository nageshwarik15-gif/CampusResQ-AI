"""
Campus Spatial Topology and Graph Model
Provides NetworkX representation of campus buildings, corridors, stairwells, rooms, and exits.
"""

import networkx as nx
from typing import Dict, Any, List, Tuple
import math

class HazardZone:
    def __init__(self, hazard_id: str, name: str, center: Tuple[float, float], lethal_radius: float, danger_radius: float):
        self.hazard_id = hazard_id
        self.name = name
        self.center = center  # (x, y) relative meters or (lat, lng)
        self.lethal_radius = lethal_radius
        self.danger_radius = danger_radius

    def distance_to(self, point: Tuple[float, float]) -> float:
        dx = self.center[0] - point[0]
        dy = self.center[1] - point[1]
        return math.sqrt(dx * dx + dy * dy)

def build_campus_building_graph(building_id: str = "CHEM_HALL") -> nx.DiGraph:
    """
    Constructs a detailed corridor/stairwell graph for a campus building.
    Coordinates are in local metric units (meters from SW corner).
    """
    G = nx.DiGraph()
    G.graph["building_id"] = building_id
    G.graph["name"] = "Chemistry Hall" if building_id == "CHEM_HALL" else building_id
    
    # Define Rooms with coordinates
    rooms = {
        "ROOM_301": {"coordinates": (10.0, 30.0), "floor": 3, "type": "lab", "occupants": 12},
        "ROOM_302": {"coordinates": (25.0, 30.0), "floor": 3, "type": "lab_chem", "occupants": 15},
        "ROOM_303": {"coordinates": (45.0, 30.0), "floor": 3, "type": "lecture_hall", "occupants": 18},
        "ROOM_304": {"coordinates": (65.0, 30.0), "floor": 3, "type": "faculty_office", "occupants": 4},
        "ROOM_201": {"coordinates": (10.0, 20.0), "floor": 2, "type": "classroom", "occupants": 25},
        "ROOM_202": {"coordinates": (35.0, 20.0), "floor": 2, "type": "classroom", "occupants": 20},
        "ROOM_101": {"coordinates": (10.0, 10.0), "floor": 1, "type": "admin", "occupants": 8},
        "ROOM_102": {"coordinates": (35.0, 10.0), "floor": 1, "type": "lobby", "occupants": 15},
    }
    
    # Define Corridor Nodes
    corridors = {
        "CORRIDOR_3_WEST": {"coordinates": (10.0, 25.0), "floor": 3, "type": "corridor"},
        "CORRIDOR_3_CENTER": {"coordinates": (35.0, 25.0), "floor": 3, "type": "corridor"},
        "CORRIDOR_3_EAST": {"coordinates": (65.0, 25.0), "floor": 3, "type": "corridor"},
        
        "CORRIDOR_2_WEST": {"coordinates": (10.0, 15.0), "floor": 2, "type": "corridor"},
        "CORRIDOR_2_CENTER": {"coordinates": (35.0, 15.0), "floor": 2, "type": "corridor"},
        "CORRIDOR_2_EAST": {"coordinates": (65.0, 15.0), "floor": 2, "type": "corridor"},
        
        "CORRIDOR_1_WEST": {"coordinates": (10.0, 5.0), "floor": 1, "type": "corridor"},
        "CORRIDOR_1_CENTER": {"coordinates": (35.0, 5.0), "floor": 1, "type": "corridor"},
        "CORRIDOR_1_EAST": {"coordinates": (65.0, 5.0), "floor": 1, "type": "corridor"},
    }
    
    # Stairwells & Exits
    junctions = {
        "STAIRWELL_WEST_3": {"coordinates": (5.0, 25.0), "floor": 3, "type": "stairwell"},
        "STAIRWELL_WEST_2": {"coordinates": (5.0, 15.0), "floor": 2, "type": "stairwell"},
        "STAIRWELL_WEST_1": {"coordinates": (5.0, 5.0), "floor": 1, "type": "stairwell"},
        
        "STAIRWELL_EAST_3": {"coordinates": (75.0, 25.0), "floor": 3, "type": "stairwell"},
        "STAIRWELL_EAST_2": {"coordinates": (75.0, 15.0), "floor": 2, "type": "stairwell"},
        "STAIRWELL_EAST_1": {"coordinates": (75.0, 5.0), "floor": 1, "type": "stairwell"},
        
        "EXIT_WEST_GROUND": {"coordinates": (0.0, 5.0), "floor": 1, "type": "safe_exit"},
        "EXIT_EAST_GROUND": {"coordinates": (80.0, 5.0), "floor": 1, "type": "safe_exit"},
        "EXIT_SOUTH_MAIN": {"coordinates": (35.0, 0.0), "floor": 1, "type": "safe_exit"},
    }
    
    # Add nodes to graph
    for nid, data in rooms.items():
        G.add_node(nid, **data, is_room=True, weight=1.0)
    for nid, data in corridors.items():
        G.add_node(nid, **data, is_room=False, weight=1.0)
    for nid, data in junctions.items():
        G.add_node(nid, **data, is_room=False, weight=1.0)
        
    G.rooms = list(rooms.keys())
    G.safe_exits = ["EXIT_WEST_GROUND", "EXIT_EAST_GROUND", "EXIT_SOUTH_MAIN"]
    
    # Bi-directional connections
    def add_bidirectional_edge(u, v, base_weight=None):
        if base_weight is None:
            c1 = G.nodes[u]["coordinates"]
            c2 = G.nodes[v]["coordinates"]
            dist = math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)
            base_weight = max(1.0, dist)
        G.add_edge(u, v, weight=base_weight)
        G.add_edge(v, u, weight=base_weight)
        
    # Connect rooms to floor corridors
    add_bidirectional_edge("ROOM_301", "CORRIDOR_3_WEST")
    add_bidirectional_edge("ROOM_302", "CORRIDOR_3_CENTER")
    add_bidirectional_edge("ROOM_303", "CORRIDOR_3_CENTER")
    add_bidirectional_edge("ROOM_304", "CORRIDOR_3_EAST")
    
    add_bidirectional_edge("ROOM_201", "CORRIDOR_2_WEST")
    add_bidirectional_edge("ROOM_202", "CORRIDOR_2_CENTER")
    
    add_bidirectional_edge("ROOM_101", "CORRIDOR_1_WEST")
    add_bidirectional_edge("ROOM_102", "CORRIDOR_1_CENTER")
    
    # Connect corridors along Floor 3
    add_bidirectional_edge("STAIRWELL_WEST_3", "CORRIDOR_3_WEST")
    add_bidirectional_edge("CORRIDOR_3_WEST", "CORRIDOR_3_CENTER")
    add_bidirectional_edge("CORRIDOR_3_CENTER", "CORRIDOR_3_EAST")
    add_bidirectional_edge("CORRIDOR_3_EAST", "STAIRWELL_EAST_3")
    
    # Connect corridors along Floor 2
    add_bidirectional_edge("STAIRWELL_WEST_2", "CORRIDOR_2_WEST")
    add_bidirectional_edge("CORRIDOR_2_WEST", "CORRIDOR_2_CENTER")
    add_bidirectional_edge("CORRIDOR_2_CENTER", "CORRIDOR_2_EAST")
    add_bidirectional_edge("CORRIDOR_2_EAST", "STAIRWELL_EAST_2")
    
    # Connect corridors along Floor 1
    add_bidirectional_edge("STAIRWELL_WEST_1", "CORRIDOR_1_WEST")
    add_bidirectional_edge("CORRIDOR_1_WEST", "CORRIDOR_1_CENTER")
    add_bidirectional_edge("CORRIDOR_1_CENTER", "CORRIDOR_1_EAST")
    add_bidirectional_edge("CORRIDOR_1_EAST", "STAIRWELL_EAST_1")
    
    # Vertical Stairwell edges (Downwards preferred for egress)
    G.add_edge("STAIRWELL_WEST_3", "STAIRWELL_WEST_2", weight=10.0)
    G.add_edge("STAIRWELL_WEST_2", "STAIRWELL_WEST_1", weight=10.0)
    G.add_edge("STAIRWELL_WEST_1", "EXIT_WEST_GROUND", weight=5.0)
    
    G.add_edge("STAIRWELL_EAST_3", "STAIRWELL_EAST_2", weight=10.0)
    G.add_edge("STAIRWELL_EAST_2", "STAIRWELL_EAST_1", weight=10.0)
    G.add_edge("STAIRWELL_EAST_1", "EXIT_EAST_GROUND", weight=5.0)
    
    # Ground floor exit to main south portal
    G.add_edge("CORRIDOR_1_CENTER", "EXIT_SOUTH_MAIN", weight=5.0)
    G.add_edge("EXIT_SOUTH_MAIN", "CORRIDOR_1_CENTER", weight=5.0)
    
    return G
