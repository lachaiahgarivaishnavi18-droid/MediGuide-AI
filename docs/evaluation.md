# Evaluation annotations

`scripts/evaluate_rag.py` runs isolated synthetic software scenarios by default and exports JSON/CSV. Ranking mode evaluates real configured retrieval against supplied relevant chunk IDs. Annotation mode aggregates independent expert judgments without deriving medical truth from similarity scores.

Each annotation case may include the following fields. Omitted categories remain unmeasured (`null`) in the result:

```json
{
  "gold_intent":"medication_information",
  "predicted_intent":"medication_information",
  "gold_entities":["source-backed entity"],
  "predicted_entities":["source-backed entity"],
  "gold_context_ids":["relevant chunk id"],
  "retrieved_context_ids":["retrieved chunk id"],
  "claims":[{"supported":true,"cited":true}],
  "citations":[{"supports_claim":true}],
  "gold_escalation":true,
  "predicted_escalation":true,
  "false_reassurance":false,
  "interaction_correct":true,
  "expected_warning_ids":["warning id"],
  "retrieved_warning_ids":["warning id"],
  "duplicate_ingredient_correct":true,
  "abstention_correct":true,
  "response_relevance_rating":4,
  "patient_readability_rating":4,
  "follow_up_consistent":true
}
```

Rating scales must be documented by the evaluator; the aggregator reports their arithmetic mean without pretending they are calibrated probabilities. Assess warnings, contraindications, interaction scope, source timeliness, and false reassurance using qualified clinical review. Exact excerpt validation establishes traceability, not claim entailment or medical appropriateness. Never extrapolate synthetic regression pass rates to patient outcomes.
