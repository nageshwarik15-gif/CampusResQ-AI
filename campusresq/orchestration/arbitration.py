"""
Algorithm 2: Multi-Agent Conflict Arbitration & Priority Sorting
Conforms strictly to IEEE 1016-2009 SDD §8.2 and SRS §3.5.
Resolves contradictory agent recommendations and sorts by Life-Safety ICS Priority Hierarchy.
"""

from typing import List, Set, Any, Union
from ..models.schemas import TacticalAction

def arbitrate_and_prioritize(
    all_actions: List[Union[TacticalAction, dict]], 
    hard_violations: Union[Set[str], List[str]]
) -> List[TacticalAction]:
    """
    Arbitrates conflicts and prioritizes actions.
    Algorithm 2 implementation from SDD §8.2.
    """
    hard_violations_set = set(hard_violations)
    
    parsed_actions: List[TacticalAction] = []
    for item in all_actions:
        if isinstance(item, dict):
            parsed_actions.append(TacticalAction(**item))
        elif isinstance(item, TacticalAction):
            parsed_actions.append(item)
            
    # 1. Filter hard-blocked actions flagged by safety guardrail
    safe_actions = [
        act for act in parsed_actions 
        if act.action_id not in hard_violations_set
    ]
    
    # 2. Sort strictly by Life-Safety ICS Priority Hierarchy
    priority_order = {
        "P1_IMMEDIATE": 1,
        "P2_HIGH": 2,
        "P3_MEDIUM": 3,
        "P4_LOW": 4
    }
    
    tier_order = {
        "TIER_A_CRITICAL": 1,
        "TIER_B_OPERATIONAL": 2,
        "TIER_C_INFORMATIONAL": 3
    }
    
    # Deduplicate by target and category to avoid redundant tasks
    seen_keys = set()
    deduped_actions = []
    for act in safe_actions:
        key = (act.category, act.target, act.tier)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped_actions.append(act)
    
    deduped_actions.sort(
        key=lambda a: (
            priority_order.get(a.priority, 5),
            tier_order.get(a.tier, 4)
        )
    )
    
    return deduped_actions
