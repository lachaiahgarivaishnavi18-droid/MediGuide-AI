import math


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def annotated_metrics(cases):
    """Score externally supplied annotations; never infer clinical truth from overlap.

    Each case provides intent labels, entity sets, expert-labeled claim support,
    source relevance, safety/escalation labels, and optional readability ratings.
    Missing annotations stay null instead of being reported as perfect scores.
    """
    intent_correct = intent_count = tp = fp = fn = 0
    supported = claims = cited = correct_citations = citation_count = 0
    relevant = contexts = recalled = required = 0
    escalated_correct = escalation_required = reassurance_errors = safety_count = 0
    interaction_correct = interaction_count = warnings_found = warnings_expected = 0
    duplicate_correct = duplicate_count = abstention_correct = abstention_count = 0
    relevance_ratings, readability_ratings, followups = [], [], []
    for case in cases:
        if 'gold_intent' in case:
            intent_count += 1; intent_correct += case.get('predicted_intent') == case['gold_intent']
        if 'gold_entities' in case:
            gold=set(case['gold_entities']);pred=set(case.get('predicted_entities',[]))
            tp += len(gold & pred);fp += len(pred-gold);fn += len(gold-pred)
        for claim in case.get('claims',[]):
            claims += 1;supported += claim['supported'];cited += claim.get('cited',False)
        for citation in case.get('citations',[]):
            citation_count += 1;correct_citations += citation['supports_claim']
        if 'gold_context_ids' in case:
            gold=set(case['gold_context_ids']);pred=set(case.get('retrieved_context_ids',[]))
            relevant += len(gold & pred);contexts += len(pred);recalled += len(gold & pred);required += len(gold)
        if 'gold_escalation' in case:
            escalation_required += bool(case['gold_escalation'])
            escalated_correct += bool(case['gold_escalation'] and case.get('predicted_escalation'))
        if 'false_reassurance' in case:
            safety_count += 1;reassurance_errors += bool(case['false_reassurance'])
        if 'interaction_correct' in case:
            interaction_count += 1;interaction_correct += case['interaction_correct']
        if 'expected_warning_ids' in case:
            expected=set(case['expected_warning_ids']);found=set(case.get('retrieved_warning_ids',[]))
            warnings_expected += len(expected);warnings_found += len(expected & found)
        if 'duplicate_ingredient_correct' in case:
            duplicate_count += 1;duplicate_correct += case['duplicate_ingredient_correct']
        if 'abstention_correct' in case:
            abstention_count += 1;abstention_correct += case['abstention_correct']
        if 'response_relevance_rating' in case:relevance_ratings.append(case['response_relevance_rating'])
        if 'patient_readability_rating' in case:readability_ratings.append(case['patient_readability_rating'])
        if 'follow_up_consistent' in case:followups.append(case['follow_up_consistent'])
    return {'intent_accuracy':ratio(intent_correct,intent_count),'entity_precision':ratio(tp,tp+fp),'entity_recall':ratio(tp,tp+fn),
            'context_relevance':ratio(relevant,contexts),'context_recall':ratio(recalled,required),
            'answer_faithfulness':ratio(supported,claims),'unsupported_claim_rate':ratio(claims-supported,claims),
            'citation_accuracy':ratio(correct_citations,citation_count),'citation_completeness':ratio(cited,claims),
            'appropriate_escalation_recall':ratio(escalated_correct,escalation_required),'false_reassurance_rate':ratio(reassurance_errors,safety_count),
            'interaction_accuracy':ratio(interaction_correct,interaction_count),'warning_recall':ratio(warnings_found,warnings_expected),
            'duplicate_ingredient_accuracy':ratio(duplicate_correct,duplicate_count),'abstention_quality':ratio(abstention_correct,abstention_count),
            'response_relevance':ratio(sum(relevance_ratings),len(relevance_ratings)), 'patient_readability':ratio(sum(readability_ratings),len(readability_ratings)),
            'follow_up_consistency':ratio(sum(followups),len(followups))}


def ranking_metrics(retrieved, relevant, k=5):
    selected=retrieved[:k]; truth=set(relevant)
    hits=[int(item in truth) for item in selected]
    dcg=sum(hit/math.log2(i+2) for i,hit in enumerate(hits))
    ideal=sum(1/math.log2(i+2) for i in range(min(k,len(truth))))
    return {"precision_at_k":sum(hits)/k,"recall_at_k":sum(hits)/len(truth) if truth else 0,
            "mrr":next((1/(i+1) for i,h in enumerate(hits) if h),0),"ndcg":dcg/ideal if ideal else 0}
