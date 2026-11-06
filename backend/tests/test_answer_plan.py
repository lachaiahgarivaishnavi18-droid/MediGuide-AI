from app.services.answer_plan import plan_passage,valid_blocks
from types import SimpleNamespace

def test_plan_keeps_qualifier_and_list_and_rejects_modified_claim():
    text='# Side effects\n\nSerious reactions are rare.\n\nExamples include:\n\n- Example A\n- Example B'
    blocks=plan_passage('What are the side effects and examples?',{'excerpt':text})
    assert blocks[0]['text']=='Serious reactions are rare.'
    assert any('Examples include:\n\n- Example A\n- Example B' in b['text'] for b in blocks)
    assert valid_blocks({'answer_blocks':blocks},SimpleNamespace(text=text))
    assert len(blocks)==2
    blocks[0]['text']='Invented medical claim'
    assert not valid_blocks({'answer_blocks':blocks},SimpleNamespace(text=text))

def test_overlapping_introduction_and_list_are_emitted_once():
    text='# Types\n\nThere are several groups of examples.\n\n- Example A\n- Example B'
    blocks=plan_passage('What groups of examples include Example A?',{'excerpt':text})
    assert len(blocks)==1
    assert blocks[0]['text'].count('There are several groups')==1
    assert valid_blocks({'answer_blocks':blocks},SimpleNamespace(text=text))

def test_answer_filters_unrequested_sections_and_preserves_unicode():
    from app.services.answer_plan import with_answer_plans
    from app.agents.response_generation import render
    items=[{'section':'Overview','excerpt':'Antibiotics do not work for viral infections such as colds.','matched_medications':[]},
           {'section':'Types of antibiotics','excerpt':'There are several types of antibiotics for different uses.','matched_medications':[]}]
    selected=with_answer_plans('Do antibiotics treat colds?',items)
    assert len(selected)==1
    assert 'Types of antibiotics' not in render(selected)
    assert 'professional\u2019s instructions' in render(selected)

def test_general_health_question_does_not_inherit_previous_medicine(db):
    from test_rag_regressions import medicine_source
    medicine_source(db)
    from app.rag.query import resolve_query
    assert resolve_query(db,'What are the symptoms of dehydration?','What is paracetamol used for?')=='What are the symptoms of dehydration?'
