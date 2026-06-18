"""Tests for chunked JSON document loading."""

from __future__ import annotations

import json

from app.pipelines.retrieval.chunk_loader import load_documents


def test_load_documents_preserves_language_metadata(tmp_path) -> None:
    payload = [
        {
            "chunk_id": "chunk-en",
            "parent_chunk_id": "parent-1",
            "url": "https://www.teg.ie/en",
            "title": "TEG",
            "language": "English",
            "content_type": "html",
            "header_path": [],
            "chunk_index": 0,
            "content": "English chunk content",
        },
        {
            "chunk_id": "chunk-ga",
            "parent_chunk_id": "parent-2",
            "url": "https://www.teg.ie/ga",
            "title": "TEG",
            "language": "Irish",
            "content_type": "html",
            "header_path": [],
            "chunk_index": 0,
            "content": "Ábhar Gaeilge",
        },
    ]
    path = tmp_path / "chunks.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    documents = load_documents(path)

    assert len(documents) == 2
    assert documents[0].metadata["language"] == "English"
    assert documents[1].metadata["language"] == "Irish"
