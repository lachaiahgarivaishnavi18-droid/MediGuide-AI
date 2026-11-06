import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e', timeout: 90000, workers: 1,
  use: { baseURL: process.env.E2E_URL || 'http://127.0.0.1:5173', channel: process.env.E2E_BROWSER || 'msedge', headless: true, viewport: {width:1440,height:1000}, screenshot:'only-on-failure' },
  outputDir: '../runtime/playwright', reporter: 'list'
})
