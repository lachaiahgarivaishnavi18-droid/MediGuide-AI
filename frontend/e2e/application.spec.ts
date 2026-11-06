import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'

test('patient browser workflow and safety gates', async ({page}) => {
  const email=`e2e-${randomUUID()}@example.test`
  const errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  try {
    const registered=await page.request.post('/api/auth/register',{data:{email,name:'Browser verification',password:randomUUID()}})
    expect(registered.status()).toBe(201)
    await page.goto('/app/dashboard')
    await expect(page.getByRole('heading',{name:'Hello, Browser.'})).toBeVisible()
    await page.screenshot({path:'../runtime/dashboard-desktop.png',fullPage:true})
    await page.getByRole('link',{name:'Ask MediGuide'}).click()
    await page.getByLabel('Your question').fill('I cannot breathe')
    await page.getByRole('button',{name:'Send question'}).click()
    await expect(page.getByText(/This could require urgent help/).first()).toBeVisible({timeout:30000})
    await expect(page.getByText('insufficient evidence').first()).toBeVisible()
    await page.goto('/app/interactions')
    await page.getByLabel('Medication 1').fill('Synthetic unknown A')
    await page.getByLabel('Medication 2').fill('Synthetic unknown B')
    await page.getByRole('button',{name:'Check documented evidence'}).click()
    await expect(page.getByText('needs professional review')).toBeVisible()
    await expect(page.getByText(/No approved medication record/)).toBeVisible()
    await page.goto('/app/agents')
    await expect(page.getByRole('heading',{name:'Agent monitor'})).toBeVisible()
    await expect(page.getByText(/completed ·/).first()).toBeVisible()
    await page.goto('/app/analytics')
    await expect(page.getByRole('heading',{name:'Reports & analytics'})).toBeVisible()
    await expect(page.getByRole('heading',{name:'Questions by category'})).toBeVisible()
    await page.setViewportSize({width:390,height:844})
    await page.goto('/app/dashboard')
    await expect(page.getByRole('heading',{name:'Hello, Browser.'})).toBeVisible()
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true)
    await page.screenshot({path:'../runtime/dashboard-mobile.png',fullPage:true})
    await page.getByRole('button',{name:'Open navigation'}).click()
    await page.getByRole('link',{name:'Education library'}).click()
    await expect(page.getByRole('heading',{name:'Patient education library'})).toBeVisible()
    expect(errors).toEqual([])
  } finally {
    const root=resolve('..')
    execFileSync(resolve(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),[resolve(root,'scripts/cleanup_test_user.py'),email],{cwd:root})
  }
})
