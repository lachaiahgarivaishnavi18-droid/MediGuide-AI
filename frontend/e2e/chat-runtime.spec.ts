import {test,expect} from '@playwright/test'
import {randomUUID} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import {resolve} from 'node:path'
import {mkdirSync,writeFileSync} from 'node:fs'

test('real user inputs, confirmations, API payloads, and rendered answers agree',async({page})=>{
  const root=resolve('..'),python=resolve(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python')
  const email=`e2e-${randomUUID()}@example.test`,results:Record<string,unknown>[]=[],errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  let runtime:Record<string,unknown>={},corpus:Record<string,unknown>={}
  try{
    const registered=await page.request.post('/api/auth/register',{data:{email,name:'Chat runtime verification',password:randomUUID()}})
    expect(registered.status()).toBe(201)
    runtime=await (await page.request.get('/api/system/status')).json()
    corpus=await (await page.request.get('/api/knowledge/status')).json()
    const direct=JSON.parse(execFileSync(python,['-c',"import sys,json;sys.path.insert(0,'backend');from app.database.session import SessionLocal;from app.rag.diagnostics import corpus_status;db=SessionLocal();print(json.dumps(corpus_status(db)));db.close()"],{cwd:root,encoding:'utf8'}))
    expect(corpus.corpus_fingerprint).toBe(direct.corpus_fingerprint)
    expect(corpus.approved_chunks).toBeGreaterThanOrEqual(220)
    await page.goto('/app/chat')
    async function capture(action:()=>Promise<unknown>,label:string){
      const count=await page.locator('.message.assistant').count()
      const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat'&&r.request().method()==='POST')
      await action()
      const response=await pending,body=await response.json(),request=response.request().postDataJSON()
      expect(response.status()).toBe(200)
      await expect(page.locator('.message.assistant')).toHaveCount(count+1,{timeout:30000})
      const latest=page.locator('.message.assistant').last()
      await expect(latest).toHaveAttribute('data-message-id',body.message_id)
      await expect(latest.locator('.message-body>strong')).toBeInViewport()
      expect(body.diagnostics.runtime_id).toBe(runtime.runtime_id)
      expect(body.diagnostics.corpus_fingerprint).toBe(corpus.corpus_fingerprint)
      expect(body.diagnostics.citation_validation).toBe('passed')
      expect(await latest.locator('.citations details').count()).toBe(body.citations.length)
      for(let i=0;i<body.citations.length;i++){
        expect(body.citations[i].supporting_quotes.length).toBeGreaterThan(0)
        for(const quote of body.citations[i].supporting_quotes){expect(body.answer).toContain(quote);expect(body.citations[i].excerpt).toContain(quote)}
        expect(await latest.locator('.citations details').nth(i).locator('a').first().getAttribute('href')).toBe(body.citations[i].url)
      }
      results.push({case:label,request:request.query,http_status:response.status(),evidence_status:body.evidence_status,clarification:body.clarification,answer:body.answer,citations:body.citations,diagnostics:body.diagnostics,rendered_message_id:await latest.getAttribute('data-message-id'),rendered_excerpt:(await latest.innerText()).slice(0,300),latest_answer_visible:true})
      return body
    }
    async function send(query:string){return capture(async()=>{await page.getByLabel('Your question').fill(query);await page.getByRole('button',{name:'Send question'}).click()},query)}
    // Use a real starter button generated from the current corpus.
    await expect(page.locator('.chat-welcome .suggestions button').first()).toBeVisible()
    const starter=await capture(()=>page.locator('.chat-welcome .suggestions button').first().click(),'source-backed starter button')
    expect(starter.citations.length).toBeGreaterThan(0)
    for(const query of ['What are the common side effects of Paracetamol?','What is ibuprofen used for?','How should paracetamol be stored?']){
      const body=await send(query);expect(body.evidence_status).toBe('LIMITED_EVIDENCE');expect(body.citations.length).toBeGreaterThan(0)
    }
    for(const typo of ['paracetomal','pharacetemol','paracetemol']){
      const body=await send(`what are the common side effects of ${typo}`)
      expect(body.clarification.kind).toBe('medicine_spelling');expect(body.citations).toHaveLength(0)
      const confirmed=await capture(()=>page.locator('.message.assistant').last().getByRole('button',{name:'Confirm paracetamol',exact:true}).click(),`explicit confirmation after ${typo}`)
      expect(confirmed.evidence_status).toBe('LIMITED_EVIDENCE');expect(confirmed.citations.length).toBeGreaterThan(0)
    }
    const followup=await capture(()=>page.locator('.message.assistant').last().locator('.followups button').first().click(),'source-backed follow-up button')
    expect(followup.citations.length).toBeGreaterThan(0)
    const storage=await send('What information is available about medication storage?')
    expect(storage.citations.length).toBeGreaterThan(0)
    const unknown=await send('What are the side effects of FictionalDrugQ?')
    expect(unknown.evidence_status).toBe('INSUFFICIENT_EVIDENCE');expect(unknown.citations).toHaveLength(0)
    await send('What are the side effects of Paracetamol?')
    await page.screenshot({path:'../runtime/chat-live-answer.png',fullPage:true})
    expect(errors).toEqual([])
  }finally{
    mkdirSync(resolve(root,'runtime'),{recursive:true})
    writeFileSync(resolve(root,'runtime/chat-runtime-results.json'),JSON.stringify({runtime,corpus,results,browser_errors:errors},null,2))
    execFileSync(python,[resolve(root,'scripts/cleanup_test_user.py'),email],{cwd:root})
  }
})
