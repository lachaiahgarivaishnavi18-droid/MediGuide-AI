import test from 'node:test'
import assert from 'node:assert/strict'
import {deploymentConfig} from './prepare_vercel.mjs'

test('API and health routes precede the SPA fallback and preserve backend paths',()=>{
  const config=deploymentConfig('https://mediguide-api.example.com')
  assert.deepEqual(config.rewrites,[
    {source:'/api/:path*',destination:'https://mediguide-api.example.com/api/:path*'},
    {source:'/health',destination:'https://mediguide-api.example.com/health'},
    {source:'/:path*',destination:'/index.html'}
  ])
})

test('cannot publish a local, insecure, credential-bearing or path-prefixed API target',()=>{
  for(const origin of ['http://example.com','https://127.0.0.1','https://[::1]','https://localhost','https://app.local','https://app.internal','https://user:password@example.com','https://example.com/api','https://example.com/?token=secret','https://example.com/#fragment'])assert.throws(()=>deploymentConfig(origin))
})
