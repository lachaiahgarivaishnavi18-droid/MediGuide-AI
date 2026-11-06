import {test,expect} from '@playwright/test'
import {randomUUID} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import {resolve} from 'node:path'
import {writeFileSync} from 'node:fs'

test('exact reported questions, rewrites and pasted refusals use the real chat API',async({page})=>{
  test.setTimeout(180000)
  const root=resolve('..'),email=`e2e-${randomUUID()}@example.test`,results:unknown[]=[],errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  try{
    expect((await page.request.post('/api/auth/register',{data:{email,name:'Query repair verification',password:randomUUID()}})).status()).toBe(201)
    await page.goto('/app/chat')
    async function send(query:string,expected='LIMITED_EVIDENCE'){
      const before=await page.locator('.message.assistant').count()
      const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat'&&r.request().method()==='POST')
      await page.getByLabel('Your question').fill(query)
      await page.getByRole('button',{name:'Send question'}).click()
      const response=await pending,body=await response.json()
      expect(response.status()).toBe(200)
      expect(response.request().postDataJSON().query).toBe(query)
      expect(body.diagnostics.original_query).toBe(query)
      expect(body.evidence_status,query).toBe(expected)
      expect(body.diagnostics.citation_validation).toBe('passed')
      await expect(page.locator('.message.assistant')).toHaveCount(before+1)
      const latest=page.locator('.message.assistant').last()
      await expect(latest).toHaveAttribute('data-message-id',body.message_id)
      await expect(latest.locator('.citations details')).toHaveCount(body.citations.length)
      if(expected==='LIMITED_EVIDENCE'){
        expect(body.citations.length).toBeGreaterThan(0)
        expect(body.diagnostics.query_variants[0]).toBe(body.diagnostics.retrieval_query)
        for(let i=0;i<body.citations.length;i++){
          const c=body.citations[i]
          expect(c.url).toMatch(/^https:\/\/(www\.nhs\.uk|medlineplus\.gov|www\.who\.int|assets\.hpra\.ie)\//)
          for(const quote of c.supporting_quotes){expect(body.answer).toContain(quote);expect(c.excerpt).toContain(quote)}
          expect(await latest.locator('.citations details').nth(i).locator('a').first().getAttribute('href')).toBe(c.url)
        }
      }else expect(body.citations).toEqual([])
      results.push({query,answer:body.answer,evidence_status:body.evidence_status,safety_status:body.safety_status,citations:body.citations,diagnostics:body.diagnostics})
      return body
    }
    for(const q of [
      'What are the common side effects of paracetamol?',
      'What is ibuprofen used for?',
      'How can I understand my medication leaflet?',
      'What are the side effects of cetirizine?',
      'Can paracetamol and cetirizine interact?',
      'What precautions should I take when using amoxicillin?',
      'What is metformin used for?'
    ]){
      const body=await send(q)
      if(q.includes('leaflet')){expect(body.answer.toLowerCase()).toContain('leaflet');expect(body.answer).not.toContain('Before any new medicine')}
      if(q.includes('and cetirizine'))expect(body.answer).toMatch(/paracetamol or ibuprofen/)
      if(q==='What are the side effects of cetirizine?'){expect(body.answer).toContain('sleepy');expect(body.citations[0].section).toMatch(/Common side effects/)}
    }
    const refusal='I could not find sufficient approved evidence in this knowledge base to answer reliably. Please consult the official patient leaflet or a pharmacist or qualified healthcare professional.'
    const echo=await send(refusal,'INSUFFICIENT_EVIDENCE')
    expect(echo.answer).toContain('send the original');expect(echo.diagnostics.retrieved_passages).toBe(0);expect(echo.diagnostics.query_variants).toEqual([])
    await send('What unwanted reactions can cetirizine cause?')
    await send('What does metformin help with?')
    await send('What if I forget to take amoxicillin?')
    await send('What precautions should I take with FictionalDrugQ?','INSUFFICIENT_EVIDENCE')
    await send('Can cetirizine and FictionalDrugQ interact?','INSUFFICIENT_EVIDENCE')
    for(const medicine of ['azithromycin','pantoprazole','aspirin','vitamin D','vitamin B12','amlodipine','ramipril'])await send(`What is ${medicine} used for?`)
    await page.screenshot({path:'../runtime/query-repair-browser.png',fullPage:false})
    expect(errors).toEqual([])
  }finally{
    writeFileSync(resolve(root,'runtime/query-repair-browser-results.json'),JSON.stringify({tested:results.length,results,browser_errors:errors},null,2),'utf8')
    execFileSync(resolve(root,'.venv/Scripts/python.exe'),[resolve(root,'scripts/cleanup_test_user.py'),email],{cwd:root})
  }
})
