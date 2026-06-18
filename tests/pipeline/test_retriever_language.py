"""Tests for language-filtered hybrid retrieval."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.pipelines.retrieval.hybrid_retriever import HybridRetriever


def _retriever_with_mock_store() -> HybridRetriever:
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever._vector_store = MagicMock()
    return retriever


@patch.object(HybridRetriever, "_build_parent_content", return_value="content")
def test_search_passes_language_filter_to_qdrant(mock_build_parent: MagicMock) -> None:
    retriever = _retriever_with_mock_store()
    retriever._vector_store = MagicMock()
    retriever._vector_store.similarity_search_with_score.return_value = [
        (
            Document(
                page_content="chunk",
                metadata={
                    "chunk_id": "c1",
                    "parent_chunk_id": "p1",
                    "title": "TEG",
                    "header_path": [],
                },
            ),
            0.9,
        )
    ]

    results = retriever.search("exam fees", top_k=5, language="English")

    assert len(results) == 1
    call_kwargs = retriever._vector_store.similarity_search_with_score.call_args.kwargs
    qdrant_filter = call_kwargs["filter"]
    assert qdrant_filter is not None
    assert qdrant_filter.must[0].key == "metadata.language"
    assert qdrant_filter.must[0].match.value == "English"
    mock_build_parent.assert_called_once()


@patch.object(HybridRetriever, "_build_parent_content", return_value="content")
def test_search_without_language_omits_filter(mock_build_parent: MagicMock) -> None:
    retriever = _retriever_with_mock_store()
    retriever._vector_store = MagicMock()
    retriever._vector_store.similarity_search_with_score.return_value = []

    retriever.search("exam fees", top_k=5)

    call_kwargs = retriever._vector_store.similarity_search_with_score.call_args.kwargs
    assert call_kwargs["filter"] is None
