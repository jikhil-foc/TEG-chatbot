# Query Retrieval & LLM Answer Workflow (Demo)

End-to-end pipeline that takes a user question, retrieves relevant content from the indexed corpus, and generates a grounded answer with citations. The QA LangGraph workflow performs **two-pass cross-lingual retrieval** (target language first, fallback second) before answer generation, with a validation retry loop.

```
Detect Language → Retrieve (target lang) → Rerank → Relevance Gate
                              ↓ (low relevance)
                    Translate Query → Retrieve (fallback lang) → Rerank → Relevance Gate
                              ↓ (still low)                              ↓ (pass)
                          Fallback                              Generate Answer → Citations → Validate
```

**Prerequisite:** Ingestion must be complete (`data/chunked_data.json`, `data/bm25_state.json`, and the Qdrant collection must exist). After upgrading to cross-lingual retrieval, **re-index** once so Qdrant payloads include `metadata.language` (see [Relation to Ingestion](#relation-to-ingestion)).

---

## How to Run (Demo)

**API**

```http
POST /api/v1/ask
Content-Type: application/json
Accept: text/event-stream

{
  "query": "What services does TEG provide?",
  "top_k": 10,
  "rerank_top_n": 5
}
```

The response is **Server-Sent Events** (`text/event-stream`):

| Event | Payload |
|-------|---------|
| `status` | `{ "type": "status", "step": "retrieve" \| "retrieve_fallback" \| "translate_fallback_query" \| "rerank" \| "generate" \| ... }` |
| `token` | `{ "type": "token", "content": "..." }` — streamed answer text |
| `done` | `{ "type": "done", "query", "answer", "language", "sources" }` |
| `error` | `{ "type": "error", "message": "..." }` |

**Final `done` event**

- `answer` — grounded reply (or canned fallback if context is too weak)
- `language` — detected query language (Irish or English)
- `sources` — cited pages/chunks with hybrid and rerank scores

---

## Pipeline Overview

```mermaid
flowchart TD
    Q[User Query] --> A[Detect Language]
    A --> B[Hybrid Retrieve target language]
    B --> C[Cohere Rerank]
    C --> D{Relevance Gate}
    D -->|top rerank score OK| E[LLM Generate Answer]
    D -->|no hits / low score| T[Translate Query]
    T --> B2[Hybrid Retrieve fallback language]
    B2 --> C2[Cohere Rerank]
    C2 --> D2{Relevance Gate}
    D2 -->|pass| E
    D2 -->|fail| F[Fallback Message]
    E --> G[Extract Citations]
    G --> H[LLM Validate]
    H -->|PASS| I[Return Answer + Sources]
    H -->|FAIL + retries left| E
    H -->|FAIL + no retries| I
    F --> I

    B -.-> B1[Qdrant teg_chunks filtered by metadata.language]
    B2 -.-> B1
```

| Step | Model / Component | Purpose |
|------|-------------------|---------|
| 1. Detect Language | Stopword scoring | Target answer language = detected query language |
| 2. Retrieve (primary) | OpenAI embeddings + BM25 + Qdrant | Search chunks tagged with target language |
| 3. Rerank | Cohere rerank API | Rescore for query–passage relevance |
| 4. Relevance Gate | Score threshold | Pass → answer; fail → fallback-language retrieval |
| 5. Translate Query | `gpt-4o-mini` | Translate question for fallback-language BM25/dense search |
| 6. Retrieve (fallback) | Hybrid search + language filter | Search the other language corpus |
| 7. Generate Answer | `gpt-4o-mini` | Grounded reply **always in target language** |
| 8. Citations | Regex on `[n]` markers | Return only cited sources |
| 9. Validate | `gpt-4o-mini` | Check groundedness; retry if needed |

---

## Step 1 — Detect Language

**What it does**

- Detects whether the user asked in Irish or English. This becomes the **target language** for the answer.
- Also computes **fallback language** (the other of English / Irish).

**Logic applied**

| Area | Logic |
|------|-------|
| Input | Raw user query string |
| Detection | **Stopword scoring** — count Irish vs English function words in the query |
| Decision | Higher count wins; ambiguous or short text defaults to **English** |
| Output | `language` (target) and `fallback_language` passed through the pipeline |

---

## Step 2 — Hybrid Retrieve (target language)

**What it does**

- Searches the Qdrant index for the `top_k` most relevant passages (default **10**) **in the target language only**.

**Logic applied**

| Area | Logic |
|------|-------|
| Retriever | Cached **HybridRetriever** (built once per process, refreshed after ingestion) |
| Language filter | Qdrant payload filter `metadata.language == target_language` |
| Dense search | Query embedded with **OpenAI `text-embedding-3-large`** → cosine similarity in Qdrant |
| Sparse search | **BM25** sparse vector from persisted `data/bm25_state.json` |
| Fusion | Qdrant **hybrid mode** — dense + sparse combined by the vector store |
| Parent expansion | Matched **child chunk** is expanded to its full **parent section** (all sibling chunks under the same `parent_chunk_id`, ordered by `chunk_index`) |
| De-duplication | Same parent section returned only once even if multiple children matched |
| Context enrichment | Breadcrumb prepended: page title + header path (`#` / `##` / `###` hierarchy) |
| Output | List of hits: `chunk_id`, `score`, `content`, `metadata` |

This is **small-to-big retrieval**: search stays precise on fine-grained chunks; the LLM receives the wider surrounding section.

---

## Step 3 — Rerank (primary pass)

**What it does**

- Rescores retrieved hits and keeps only the top `rerank_top_n` (default **5**) for LLM context.

**Logic applied**

| Area | Logic |
|------|-------|
| Model | **Cohere rerank API** (configured via `COHERE_API_KEY`) |
| Scoring | Each `(query, passage)` pair scored jointly — reads query and content together |
| Language boost | Optional bonus when chunk language matches target language (`rerank_language_boost`) |
| Sorting | Hits reordered by `rerank_score` descending; top N kept |
| Output | Same hit shape plus `rerank_score` on each result |

---

## Step 4 — Relevance Gate (primary pass)

**What it does**

- Decides whether target-language context is strong enough to answer, or whether to try fallback-language retrieval.

**Logic applied**

| Area | Logic |
|------|-------|
| No results | Route to **translate + fallback retrieve** |
| Score check | Compare **top `rerank_score`** against `rerank_relevance_threshold` (default **0.0**) |
| Pass | Continue to **generate answer** |
| Fail | **Translate query** and search fallback language — do not return canned fallback yet |

---

## Step 5 — Translate Query (fallback pass only)

**What it does**

- Translates the user's question into the fallback language so BM25 and dense search work against the other corpus.

**Logic applied**

| Area | Logic |
|------|-------|
| Model | **`gpt-4o-mini`** at `temperature=0` |
| Input | `effective_query` (or raw query) |
| Output | `fallback_search_query` used for the second retrieval pass |
| Failure | Falls back to the untranslated query |

---

## Step 6 — Hybrid Retrieve (fallback language)

**What it does**

- Same as Step 2, but filters Qdrant to `metadata.language == fallback_language` and uses the translated query.

---

## Step 7 — Rerank + Relevance Gate (fallback pass)

**What it does**

- Reranks fallback-language hits (no target-language score boost). If the gate passes, continue to answer generation; otherwise return the canned fallback message in the **target language**.

---

## Step 8 — Generate Answer (LLM)

**What it does**

- Produces a concise, grounded answer using only the reranked context.

**Logic applied**

| Area | Logic |
|------|-------|
| Model | **`gpt-4o-mini`** at `temperature=0` |
| Context format | Numbered blocks `[1] Title (url)\ncontent` — one per reranked hit |
| System prompt | Answer **only** from provided context; cite inline as `[1]`, `[2][3]`; say "don't know" if insufficient |
| Language | Always respond in **target language** (detected query language). When context came from the fallback pass, explicitly translate facts from the other language into the target language. |
| Grounding rule | Must not invent facts or cite sources outside the numbered context |

---

## Step 9 — Citations

**What it does**

- Builds the `sources` list returned to the client.

**Logic applied**

| Area | Logic |
|------|-------|
| Parse answer | Regex extracts `[n]` citation markers from the generated text |
| Cited sources | Only reranked hits referenced by `[n]` are included (in citation order) |
| No citations in answer | Falls back to returning **all** reranked hits as sources |
| Source fields | `chunk_id`, `url`, `title`, hybrid `score`, `rerank_score` |

---

## Step 10 — Validate (LLM)

**What it does**

- Checks that the answer is faithful to the context and citations are valid.

**Logic applied**

| Area | Logic |
|------|-------|
| Model | **`gpt-4o-mini`** at `temperature=0` (separate validation prompt) |
| Checks | (1) Answer fully grounded — no invented facts; (2) every `[n]` refers to a valid context number |
| Verdict | Model replies **PASS** or **FAIL** (single word) |
| Retry loop | On **FAIL**, regenerate answer (up to `qa_max_validation_retries`, default **2**) |
| Exhausted retries | Return the last answer anyway |

---

## Configuration (Demo Knobs)

| Parameter | Default | Effect |
|-----------|---------|--------|
| `query` | required | User question (1–4000 chars) |
| `top_k` | `10` | Hybrid-search candidates to retrieve |
| `rerank_top_n` | `5` | Passages passed to the LLM as context |
| `rerank_relevance_threshold` | `0.0` | Minimum top rerank score to attempt an LLM answer |
| `qa_max_validation_retries` | `2` | Max answer regenerations when validation fails |

**Environment**

- `OPENAI_API_KEY` — embeddings (retrieve), chat (answer, validate, query translation)
- `COHERE_API_KEY` — reranking
- Qdrant at `http://localhost:6333` (default collection: `teg_chunks`)

**Re-index after upgrade**

Run the embedding index (or full ingestion) with `recreate=true` if needed so every Qdrant point includes `metadata.language` and the language payload index exists:

```bash
python scripts/embedding.py index --recreate
```

---

## End-to-End Example (English query, Irish context)

1. User asks: *"What services does TEG provide?"*
2. Language detected → target **English**, fallback **Irish**
3. Hybrid search (English filter) returns weak matches → relevance gate fails
4. Query translated to Irish → hybrid search (Irish filter) finds relevant passages
5. Cohere reranker keeps top 5 passages
6. LLM generates an **English** answer from Irish context, citing `[1][2]`
7. Citations node returns cited sources; validator confirms groundedness

## End-to-End Example (Irish query)

1. User asks: *"Cad iad na seirbhísí a chuireann TEG ar fáil?"*
2. Language detected → target **Irish**
3. Hybrid search (Irish filter) finds relevant pages → relevance gate passes on first pass
4. LLM generates Irish answer citing `[1][2]`
5. Validator confirms groundedness → response sent to client

If both retrieval passes fail the relevance gate, the user gets the canned fallback in the **target language** — without calling the answer LLM.

---

## Relation to Ingestion

| Ingestion produces | Retrieval uses |
|--------------------|----------------|
| Child chunks in Qdrant (dense + sparse vectors) | Hybrid search targets |
| `metadata.language` on each chunk (`English` / `Irish`) | Language-filtered primary and fallback retrieval |
| `parent_chunk_id` on each chunk | Parent expansion at retrieve time |
| `data/bm25_state.json` | Sparse BM25 query encoding |
| Page title, URL, header path, language metadata | Breadcrumbs, citations, source cards |

See [ingestion-workflow.md](./ingestion-workflow.md) for how the index is built.
