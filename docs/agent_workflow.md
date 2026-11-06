# Agent workflow

1. Query understanding classifies a bounded set of intents and blocks treatment modification requests.
2. Safety escalation checks conservative urgent-language rules before any source retrieval or external LLM call.
3. Entity recognition matches exact curated generic/brand names and dosage-unit expressions.
4. Knowledge retrieval applies the approved/nonsynthetic gate and hybrid retrieval.
5. Medication safety checks documented interactions and ingredient duplication and retains uncertainty.
6. Evidence evaluation uses `INSUFFICIENT_EVIDENCE`, `LIMITED_EVIDENCE`, or a curator-marked `CONFLICTING_EVIDENCE`. High confidence is deliberately not assigned by similarity alone.
7. Patient education selects passages with an extractive, API, or local provider.
8. Response generation formats exact passages with a bounded nonclinical introduction or returns a fixed abstention/safety message.
9. Citation validation reloads original chunks/documents and verifies approval, exact text, parent IDs, and the response template. Unsupported output is discarded.
10. Conversation orchestrator compiles and invokes the graph and records timings. Errors abort the transaction and return a transparent 503; unchecked output is not emitted.

The `/chat/stream` endpoint emits an SSE answer only after the entire pipeline passes. This is buffered validated delivery, not token-by-token generation. The monitor shows operational statuses and timings, never private chain-of-thought. Its diagram is a conceptual workflow; selected-run metadata indicates which nodes actually executed.
