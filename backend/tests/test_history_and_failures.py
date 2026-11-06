from app.api import routes


def test_clear_history_includes_all_messages(patient):
    for _ in range(2):
        assert patient.post('/api/chat',json={'query':'Unknown reference question'}).status_code==200
    assert len(patient.get('/api/conversations').json())==2
    assert patient.delete('/api/conversations').status_code==204
    assert patient.get('/api/conversations').json()==[]
    assert patient.get('/api/agents/executions').json()==[]


def test_failed_provider_is_visible_without_unchecked_output(patient,monkeypatch):
    def unavailable(*args):
        raise RuntimeError('Test provider unavailable')
    monkeypatch.setattr(routes,'run',unavailable)
    response=patient.post('/api/chat',json={'query':'Source reference question'})
    assert response.status_code==503
    executions=patient.get('/api/agents/executions').json()
    assert executions[0]['evidence_status']=='SOURCE_UNAVAILABLE'
    assert executions[0]['trace'][0]['status']=='failed'
    assert patient.get('/api/openapi.json').status_code==200
