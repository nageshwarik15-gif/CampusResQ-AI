import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from campusresq.rag.database import rag_db
from campusresq.rag.validator import validate_action_citation, audit_plan_citations

def test_rag_hybrid_search():
    results = rag_db.hybrid_search(
        query="chemical spill hexane solvent in chemistry hall",
        building_id="CHEM_HALL",
        hazard_type="HAZMAT",
        top_k=3
    )
    assert len(results) > 0
    top = results[0]
    assert "relevance_score" in top
    assert "rrf_score" in top
    # Should retrieve Hazardous Material Incident Protocol or SDS #CHEM-041
    assert "CHEM" in top["doc_id"].upper() or "HAZMAT" in str(top["hazard_categories"]).upper()

def test_citation_validator():
    valid_citation = {
        "document_title": "Hazardous Material Incident Protocol",
        "section": "4.3.2",
        "page": 87
    }
    assert validate_action_citation(valid_citation) is True
    
    fake_citation = {
        "document_title": "Made Up Fiction Runbook",
        "section": "99.9",
        "page": 999
    }
    assert validate_action_citation(fake_citation) is False

if __name__ == "__main__":
    test_rag_hybrid_search()
    test_citation_validator()
    print("ALL RAG TESTS PASSED!")
