"""
Algorithm 4: Deterministic Gating Enforcement
Conforms to IEEE 1016-2009 SDD §8.4 and SRS §3.4, §7.2.
Guarantees zero autonomous execution of Tier-A Critical actions.
"""

from typing import List, Any, Optional
from .signature import SecurityGatingError, compute_plan_sha256, commander_key_mgr

class HITLGatingAuditTracker:
    def __init__(self):
        self.total_attempted_tier_a: int = 0
        self.properly_gated_tier_a: int = 0
        self.rejected_violations: int = 0

    def compute_hgcm(self) -> float:
        """
        HGCM = (Properly Gated Tier-A Actions / Total Attempted Tier-A Actions) * 100%
        Target Benchmark: 100.0%
        """
        if self.total_attempted_tier_a == 0:
            return 100.0
        return round((self.properly_gated_tier_a / self.total_attempted_tier_a) * 100.0, 2)

gating_tracker = HITLGatingAuditTracker()

def enforce_hitl_dispatch_gate(
    action_plan: List[Any], 
    commander_signature: Optional[str] = None,
    expected_hash: Optional[str] = None
) -> bool:
    """
    Guarantees that Tier-A actions NEVER execute without a verified human signature.
    Algorithm 4 implementation from SDD §8.4.
    """
    tier_a_actions = []
    for a in action_plan:
        tier = getattr(a, "tier", None)
        if tier is None and isinstance(a, dict):
            tier = a.get("tier")
        if tier == "TIER_A_CRITICAL":
            tier_a_actions.append(a)

    if len(tier_a_actions) > 0:
        gating_tracker.total_attempted_tier_a += len(tier_a_actions)
        
        if not commander_signature:
            gating_tracker.rejected_violations += len(tier_a_actions)
            raise SecurityGatingError("CRITICAL VIOLATION: Tier-A actions attempted without human signature!")

        plan_hash = expected_hash or compute_plan_sha256(action_plan)
        
        # Verify cryptographic signature
        is_valid = commander_key_mgr.verify_signature(plan_hash, commander_signature)
        if not is_valid:
            gating_tracker.rejected_violations += len(tier_a_actions)
            raise SecurityGatingError("CRITICAL VIOLATION: Invalid cryptographic signature on Tier-A dispatch!")

        gating_tracker.properly_gated_tier_a += len(tier_a_actions)
        
    return True
