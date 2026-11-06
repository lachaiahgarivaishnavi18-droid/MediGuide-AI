import { test,expect } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

test('official-reference RAG returns cited evidence and preserves abstention',async({page})=>{
  const email=`e2e-${randomUUID()}@example.test`,errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  try{
    expect((await page.request.post('/api/auth/register',{data:{email,name:'RAG verification',password:randomUUID()}})).status()).toBe(201)
    const status=await (await page.request.get('/api/knowledge/status')).json()
    expect(status.available_documents).toBeGreaterThanOrEqual(3)
    expect(status.approved_chunks).toBeGreaterThan(0)
    await page.goto('/app/chat')
    // Wait for a new assistant message rather than relying on the disabled state
    // (the empty composer also disables Send after a successful response).
    const send=async(query:string)=>{
      const before=await page.locator('.message.assistant').count()
      await page.getByLabel('Your question').fill(query)
      await page.getByRole('button',{name:'Send question'}).click()
      await expect(page.locator('.message.assistant')).toHaveCount(before+1,{timeout:30000})
    }
    await send('What are the common side effects of Paracetamol?')
    let answer=page.locator('.message.assistant').last()
    await expect(answer.locator('.evidence-label')).toHaveText(/limited evidence/)
    await expect(answer).toContainText('very rarely')
    const nhs=answer.locator('.citations details').filter({hasText:'Paracetamol for adults'}).first()
    await nhs.locator('summary').click()
    await expect(nhs.getByRole('link',{name:'Open original source'})).toHaveAttribute('href','https://www.nhs.uk/medicines/paracetamol-for-adults/')
    await expect(nhs).toContainText('Source retrieved:')
    await expect(nhs).toContainText('Adults aged 18 or over')
    await page.screenshot({path:'../runtime/paracetamol-evidence.png',fullPage:true})
    await send('How should it be stored?')
    answer=page.locator('.message.assistant').last()
    await expect(answer.locator('.evidence-label')).toHaveText(/limited evidence/)
    await expect(answer.locator('.citations')).toContainText('HPRA-hosted patient leaflet')
    await send('What are the common side effects of FictionalDrugQ?')
    answer=page.locator('.message.assistant').last()
    await expect(answer.locator('.evidence-label')).toHaveText(/insufficient evidence/)
    await expect(answer.locator('.citations')).toHaveCount(0)
    await send('What are the common side effects of ibuprofen?')
    answer=page.locator('.message.assistant').last()
    await expect(answer.locator('.evidence-label')).toHaveText(/limited evidence/)
    await expect(answer.locator('.citations')).toContainText('Ibuprofen for adults')
    await expect(answer.locator('.citations')).not.toContainText('Paracetamol for adults')
    expect(errors).toEqual([])
  }finally{
    const root=resolve('..')
    execFileSync(resolve(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),[resolve(root,'scripts/cleanup_test_user.py'),email],{cwd:root})
  }
})
