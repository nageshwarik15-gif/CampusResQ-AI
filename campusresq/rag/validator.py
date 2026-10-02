"""
SOP Citation & Grounding Validator
Validates tactical action citations against the official campus knowledge base.
Conforms to SDD §4.4 and SRS §5.2.
"""

from typing import Dict, Any, List
from .knowledge_base import CAMPUS_KNOWLEDGE_DOCS

def validate_action_citation(citation: Dict[str, Any]) -> bool:
    """
    Checks if a citation provided in a TacticalAction maps directly to an indexed SOP/SDS/Blueprint.
    """
    if not citation:
        return False
        
    doc_title = citation.get("document_title", "").lower().strip()
    sec_id = str(citation.get("section", "")).lower().strip()
    
    for doc in CAMPUS_KNOWLEDGE_DOCS:
        # Match title or section_id
        if (doc_title and (doc_title in doc["title"].lower() or doc["title"].lower() in doc_title)) or \
           (sec_id and sec_id in doc["section_id"].lower()):
            return True
            
    return False

def audit_plan_citations(actions: List[Any]) -> Dict[str, Any]:
    """
    Audits a list of TacticalAction objects for citation grounding.
    """
    total = len(actions)
    if total == 0:
        return {"grounded_count": 0, "total_count": 0, "ratio": 1.0, "violations": []}
        
    grounded = 0
    violations = []
    
    for act in actions:
        cit = getattr(act, "sop_citation", None)
        if isinstance(act, dict):
            cit = act.get("sop_citation", {})
            act_id = act.get("action_id", "UNKNOWN")
        else:
            act_id = getattr(act, "action_id", "UNKNOWN")
            
        if validate_action_citation(cit):
            grounded += 1
        else:
            violations.append(act_id)
            
    return {
        "grounded_count": grounded,
        "total_count": total,
        "ratio": round(grounded / total, 4),
        "violations": violations
    }
