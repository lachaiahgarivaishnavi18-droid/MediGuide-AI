import {test,expect} from '@playwright/test'
import {randomUUID} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import {resolve} from 'node:path'
import {writeFileSync} from 'node:fs'

test('20 medical questions traverse the browser, API, semantic corpus and citation renderer',async({page})=>{
  test.setTimeout(180000)
  const root=resolve('..'),email=`e2e-${randomUUID()}@example.test`,results:unknown[]=[],errors:string[]=[]
  const questions=[
    'What are the side effects of paracetamol?', 'How should paracetamol be stored?',
    'What is ibuprofen used for?', 'What are the side effects of ibuprofen?', 'Who can take ibuprofen?',
    'Does ibuprofen interact with warfarin?', 'What is cetirizine used for?', 'Can cetirizine make me feel sleepy?',
    'Who can take cetirizine?', 'How should cetirizine be stored?',
    'What is amoxicillin used for?', 'What are the side effects of amoxicillin?',
    'Do antibiotics treat colds?', 'What are the symptoms of dehydration?', 'What causes headaches?',
    'How can I prevent a common cold?', 'What is a healthy diet?', 'What are the benefits of physical activity?',
    'How should medicines be stored?', 'What are common medicine side effects?'
  ]
  page.on('pageerror',error=>errors.push(error.message))
  try{
    expect((await page.request.post('/api/auth/register',{data:{email,name:'Expanded coverage verification',password:randomUUID()}})).status()).toBe(201)
    const corpus=await(await page.request.get('/api/knowledge/status')).json()
    expect(corpus.embedding_provider).toBe('fastembed')
    expect(corpus.available_documents).toBeGreaterThanOrEqual(36)
    await page.goto('/app/chat')
    for(const question of questions){
      const before=await page.locator('.message.assistant').count()
      const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat'&&r.request().method()==='POST')
      await page.getByLabel('Your question').fill(question)
      await page.getByRole('button',{name:'Send question'}).click()
      const response=await pending,body=await response.json()
      expect(response.status()).toBe(200)
      expect(response.request().postDataJSON().query).toBe(question)
      expect(body.evidence_status,question).toBe('LIMITED_EVIDENCE')
      expect(body.diagnostics.citation_validation).toBe('passed')
      expect(body.diagnostics.corpus_fingerprint).toBe(corpus.corpus_fingerprint)
      expect(body.citations.length).toBeGreaterThan(0)
      expect(body.answer).not.toMatch(/\u00c2\u00a0|\u00e2\u20ac|\ufffd/)
      expect(body.answer).toContain('professional\u2019s instructions')
      const normalizedQuotes:string[]=[]
      await expect(page.locator('.message.assistant')).toHaveCount(before+1)
      const latest=page.locator('.message.assistant').last()
      await expect(latest).toHaveAttribute('data-message-id',body.message_id)
      await expect(latest.locator('.citations details')).toHaveCount(body.citations.length)
      for(let i=0;i<body.citations.length;i++){
        const citation=body.citations[i]
        expect(citation.supporting_quotes.length).toBeGreaterThan(0)
        for(const quote of citation.supporting_quotes){
          expect(citation.excerpt).toContain(quote);expect(body.answer).toContain(quote)
          const normalized=quote.replace(/\s+/g,' ')
          expect(normalizedQuotes.some(previous=>previous.includes(normalized)||normalized.includes(previous))).toBe(false)
          normalizedQuotes.push(normalized)
        }
        expect(await latest.locator('.citations details').nth(i).locator('a').first().getAttribute('href')).toBe(citation.url)
      }
      if(question==='Do antibiotics treat colds?')expect(body.answer).toMatch(/do not work for viral infections/)
      if(question==='Do antibiotics treat colds?')expect(body.answer).not.toContain('Types of antibiotics')
      if(question==='Can cetirizine make me feel sleepy?')expect(body.answer).toMatch(/sleepy and tired/)
      if(question==='Does ibuprofen interact with warfarin?')expect(body.answer).toMatch(/anticoagulants \(such as warfarin/)
      results.push({question,http_status:response.status(),evidence_status:body.evidence_status,answer:body.answer,citations:body.citations,diagnostics:body.diagnostics,rendered_message_id:await latest.getAttribute('data-message-id')})
    }
    expect(errors).toEqual([])
    await page.screenshot({path:'../runtime/expanded-chat.png',fullPage:false})
  }finally{
    writeFileSync(resolve(root,'runtime/expanded-browser-results.json'),JSON.stringify({tested:results.length,results,browser_errors:errors},null,2))
    execFileSync(resolve(root,'.venv/Scripts/python.exe'),[resolve(root,'scripts/cleanup_test_user.py'),email],{cwd:root})
  }
})
