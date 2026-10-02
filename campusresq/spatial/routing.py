"""
Algorithm 1: Hazard-Weighted Dynamic Evacuation Pathing
Conforms strictly to IEEE 1016-2009 SDD §8.1.
Combines spatial building topology with dynamic plume/fire penalty costs.
"""

import networkx as nx
from typing import Dict, Any, List, Union
from .campus_graph import HazardZone

def compute_evacuation_routes(
    floor_graph: nx.DiGraph, 
    hazard_zones: List[HazardZone], 
    safe_exits: List[str]
) -> Dict[str, Any]:
    """
    Computes optimal, safe evacuation paths avoiding hazard perimeters.
    floor_graph: NetworkX DiGraph representing corridors and stairwells.
    hazard_zones: List of polygons/circles with threat penalty weights.
    safe_exits: Target egress points on ground floor.
    """
    cost_graph = floor_graph.copy()
    
    # 1. Apply hazard penalties to graph nodes & edges
    for node, data in cost_graph.nodes(data=True):
        node_point = data.get("coordinates", (0.0, 0.0))
        for hazard in hazard_zones:
            dist = hazard.distance_to(node_point)
            if dist <= hazard.lethal_radius:
                cost_graph.nodes[node]["weight"] = float("inf")  # Impassable
            elif dist <= hazard.danger_radius:
                penalty = 1.0 + (hazard.danger_radius - dist) * 10.0
                curr_w = cost_graph.nodes[node].get("weight", 1.0)
                cost_graph.nodes[node]["weight"] = curr_w * penalty

    # Also penalize edge traversals where target or source node is penalized
    for u, v in cost_graph.edges():
        u_w = cost_graph.nodes[u].get("weight", 1.0)
        v_w = cost_graph.nodes[v].get("weight", 1.0)
        if math_is_inf(u_w) or math_is_inf(v_w):
            cost_graph.edges[u, v]["weight"] = float("inf")
        else:
            base_edge_w = cost_graph.edges[u, v].get("weight", 1.0)
            cost_graph.edges[u, v]["weight"] = base_edge_w * ((u_w + v_w) / 2.0)

    # 2. Compute shortest paths to nearest uncompromised exit
    routes = {}
    path_details = {}
    rooms = getattr(floor_graph, "rooms", [n for n, d in floor_graph.nodes(data=True) if d.get("is_room", False)])
    
    for room_node in rooms:
        viable_paths = []
        for exit_node in safe_exits:
            try:
                path = nx.shortest_path(cost_graph, source=room_node, target=exit_node, weight="weight")
                cost = nx.shortest_path_length(cost_graph, source=room_node, target=exit_node, weight="weight")
                if cost < float("inf"):
                    viable_paths.append((cost, path))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        
        if viable_paths:
            viable_paths.sort(key=lambda x: x[0])
            best_cost, best_path = viable_paths[0]
            routes[room_node] = best_path
            path_details[room_node] = {
                "destination_exit": best_path[-1],
                "path": best_path,
                "cost": round(best_cost, 2),
                "safe": True
            }
        else:
            routes[room_node] = "SHELTER_IN_PLACE_SEAL_ROOM"  # Fallback
            path_details[room_node] = {
                "destination_exit": None,
                "path": [room_node],
                "cost": float("inf"),
                "safe": False,
                "action": "SHELTER_IN_PLACE_SEAL_ROOM"
            }
            
    return {
        "routes": routes,
        "details": path_details,
        "uncompromised_exits": [e for e in safe_exits if cost_graph.nodes[e].get("weight", 1.0) < float("inf")]
    }

def math_is_inf(val: float) -> bool:
    return val == float("inf") or val == float("-inf")
