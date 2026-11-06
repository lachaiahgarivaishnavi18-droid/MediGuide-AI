# RAG repair: missing evidence for basic medicine questions

## Root cause

The active SQLite database contained **0 knowledge documents and 0 chunks**. No medical PDFs had been uploaded, no approved clinical corpus existed, and there were no source vectors to search. FAISS was a local in-process index constructed from approved relational chunks, not a remote vector database with a connectivity problem. The initial synthetic seed deliberately created roles only. The frontend was accurately displaying the backend's abstention; it was not replacing a successful answer with “Insufficient Evidence”.

Additional retrieval defects would have affected a populated corpus: heading changes could relabel text carried from the preceding section; entire previous questions were appended to short new questions, causing cross-medicine/topic contamination; generic terms such as “side effects” counted as a relevance anchor; and a fixed hash-vector similarity veto could discard exact lexical evidence. Citation validation also needed to verify source URLs/titles rather than only passage text and IDs.

## Changes

- Added a fixed, bounded official-reference importer for NHS adult paracetamol, NHS adult ibuprofen, and the current HPRA-hosted Paracetamol 500mg film-coated tablet leaflet. The obsolete `www.hpra.ie/img/uploaded/...` URL returned 404; the current `assets.hpra.ie/products/Human/22017/...pdf` URL was fetched and verified instead. No restricted-site scraping or arbitrary URL loader was introduced.
- Imported **3 nonsynthetic source documents and 27 chunks** into the active database. The PDF contains four pages. Download hashes, original links, issuing/source organizations, product/population scope, retrieval dates, source update/revision dates, and licence/usage metadata are retained. Raw reference downloads remain under ignored `runtime/sources`; they are not committed as an unrestricted redistribution dataset.
- Official-manifest imports are explicitly enabled by the operator's request and repeatable without duplicate documents. Ordinary administrator uploads remain pending approval. Unknown, synthetic, unapproved, or expired sources are excluded. Scanned/blank PDFs receive an OCR-required error instead of a false index success.
- Preserved section boundaries and confined overlap to a section. Side-effect/warning sections remain intact so rare/common frequency labels and important warnings cannot be separated. HTML extraction excludes navigation; PDFs use ordered text and recognize real numbered uppercase leaflet headings rather than table-of-contents entries.
- Added exact controlled medicine/brand matching and section-topic eligibility before BM25/FAISS rank fusion. General adult questions prefer the matching general-education source; specific formulation questions retain the product leaflet context. Unknown medicines cannot borrow evidence from another medicine merely because both contain “side effects”. No fuzzy medication equivalence is assumed.
- Replaced whole-question history concatenation with explicit follow-up subject resolution. A new named medicine, including an unknown one, never inherits the previous drug. Pronoun-only follow-ups can recover the last explicit known medicine.
- Changed the lexical ranker from Okapi BM25 to BM25Plus: positive IDF prevents inverted negative rankings in small eligible medicine/topic corpora. Exact lexical anchors are still required; a nonzero rank score is never proof of clinical correctness.
- Cached FAISS/BM25 corpora by indexed content plus embedding configuration. Approval, withdrawal, expiry and content changes are applied before cache use; stale vectors cannot override the eligibility/validation gates. Exported FAISS vectors now use the same title/section/text representation as runtime retrieval and are reopened for a dimensional/count roundtrip check.
- Rehydrate citation provenance from database records and reject fabricated URLs, titles, sections, passages or expired documents. Source dates, scope, attribution and original links appear in expanded citations. NHS content carries the required OGL attribution and copy date. Exact source passages remain the factual output; no unsupported “common side effects” list is generated when the reference states otherwise.
- Added corpus/embedding/retrieval diagnostics and a chat availability indicator, so an empty or expired corpus is distinguishable from an available corpus with no evidence for a particular question.

## Reproduce

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/import_trusted_references.py
.\.venv\Scripts\python.exe scripts/build_vector_index.py
.\.venv\Scripts\python.exe scripts/diagnose_rag.py
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q backend/tests
```

The importer fetches only the explicit manifest, checks robots policies, limits downloads, refuses redirects/structure changes, and aborts without replacing the corpus when a source cannot be verified. It does not create fictional fallback content. NHS copies expire from retrieval after seven days; this product leaflet after thirty days under the local refresh policy. Rerun the importer to verify and refresh them. A source's publication/review date is distinct from its retrieval date; neither is a clinical certification.

Authenticated administrators can inspect `POST /api/knowledge/diagnose` with `{"query":"What are the common side effects of Paracetamol?"}`. It reports corpus counts, source eligibility, embedding dimensions/norm, matched medicine/topic, actual passages and BM25/vector/fusion scores. Patients can read aggregate `/api/knowledge/status`, but cannot invoke admin retrieval or change source approval.

The configured embedding provider remains the transparent offline **512-dimensional hashed-feature** development fallback, combined with BM25 and exact provenance/topic gates. This repair does not pretend a semantic model was downloaded. The optional Sentence Transformers implementation remains available through configuration and requires its own model-based evaluation. Similarity scores are not medical confidence.

## Expected outcomes

| Question | Expected result |
|---|---|
| Common side effects of Paracetamol | Cited NHS side-effects passage plus the matching official leaflet section; frequency wording preserved |
| What is Paracetamol used for? | Cited purpose sections |
| How should Paracetamol be stored? | Product-specific HPRA-hosted leaflet storage section |
| Common side effects / uses of ibuprofen | Relevant NHS sections only |
| Side effects of Panadol | Verified source-heading brand alias resolves to paracetamol |
| Side effects of amoxicillin or an unknown medicine | Insufficient evidence with no unrelated citations |
| Ibuprofen storage (no storage reference imported) | Insufficient evidence |
| Personal dose increase / possible emergency | Existing treatment-modification refusal or urgent escalation; no normal medical answer |

`runtime/trusted-reference-import.json`, `runtime/index/manifest.json`, `runtime/rag-diagnostics.json`, and browser test artifacts record the actual local run. These software checks do not establish clinical validity, comprehensive drug coverage, or personal treatment suitability.

Reference origins: [NHS paracetamol](https://www.nhs.uk/medicines/paracetamol-for-adults/), [NHS ibuprofen](https://www.nhs.uk/medicines/ibuprofen-for-adults/), [HPRA-hosted patient leaflet](https://assets.hpra.ie/products/Human/22017/7871bfd4-8dbb-41a3-aa04-117483654ca6.pdf), and [NHS reuse terms](https://www.nhs.uk/our-policies/terms-and-conditions/).
