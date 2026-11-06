import pytest
from app.evaluation.metrics import ranking_metrics
from app.evaluation.metrics import annotated_metrics


def test_ranking_metrics():
    scores=ranking_metrics(['a','x','b'],['a','b'],3)
    assert scores['precision_at_k']==pytest.approx(2/3)
    assert scores['recall_at_k']==1 and scores['mrr']==1
    assert 0<scores['ndcg']<1
    assert ranking_metrics([],['a'])['recall_at_k']==0


def test_annotated_metrics_preserve_unknowns_and_errors():
    scores=annotated_metrics([{'gold_intent':'education','predicted_intent':'education','gold_entities':['a','b'],'predicted_entities':['a','c'],
                             'claims':[{'supported':True,'cited':True},{'supported':False,'cited':False}],
                             'citations':[{'supports_claim':False}],'gold_escalation':True,'predicted_escalation':False,'false_reassurance':True}])
    assert scores['intent_accuracy']==1
    assert scores['entity_precision']==scores['entity_recall']==0.5
    assert scores['answer_faithfulness']==scores['unsupported_claim_rate']==0.5
    assert scores['citation_accuracy']==0 and scores['citation_completeness']==0.5
    assert scores['appropriate_escalation_recall']==0 and scores['false_reassurance_rate']==1
    assert scores['patient_readability'] is None
