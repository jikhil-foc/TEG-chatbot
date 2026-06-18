"""Citation extraction node.

Parses ``[n]`` markers from the grounded answer and attaches matching sources
for the API response.
"""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.citation_parser import extract_cited_sources


def citations_node(state: QAState) -> dict:
    reranked = state.get("reranked", [])
    answer = state.get("answer", "")
    sources = extract_cited_sources(answer, reranked)
    steps = list(state.get("steps_completed", []))
    steps.append("citations")
    return {"sources": sources, "steps_completed": steps}
