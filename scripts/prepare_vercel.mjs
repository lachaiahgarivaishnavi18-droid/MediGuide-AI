import {writeFile} from 'node:fs/promises'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {resolve} from 'node:path'
import {isIP} from 'node:net'

export function deploymentConfig(value){
  const origin=new URL(value)
  const host=origin.hostname.toLowerCase()
  if(origin.protocol!=='https:'||origin.username||origin.password||origin.search||origin.hash||origin.pathname!=='/'||
     !host.includes('.')||host.endsWith('.localhost')||host.endsWith('.local')||host.endsWith('.internal')||isIP(host.replace(/^\[|\]$/g,''))){
    throw new Error('Supply the public HTTPS backend origin, without credentials, a path, query parameters, or a local/IP address.')
  }
  return {
    $schema:'https://openapi.vercel.sh/vercel.json',
    framework:'vite',buildCommand:'npm run build',outputDirectory:'dist',
    rewrites:[
      {source:'/api/:path*',destination:origin.origin+'/api/:path*'},
      {source:'/health',destination:origin.origin+'/health'},
      {source:'/:path*',destination:'/index.html'}
    ],
    headers:[{source:'/:path*',headers:[
      {key:'X-Content-Type-Options',value:'nosniff'},
      {key:'Referrer-Policy',value:'no-referrer'},
      {key:'X-Frame-Options',value:'DENY'}
    ]}]
  }
}

async function main(){
  const index=process.argv.indexOf('--backend-url')
  if(index<0||!process.argv[index+1])throw new Error('Usage: node scripts/prepare_vercel.mjs --backend-url https://YOUR-HOSTED-BACKEND')
  const config=deploymentConfig(process.argv[index+1])
  const backend=new URL(config.rewrites[1].destination).origin
  const response=await fetch(backend+'/health',{signal:AbortSignal.timeout(15000),redirect:'error'})
  if(!response.ok||(await response.json()).status!=='ok')throw new Error('Backend health check failed; deployment configuration was not written.')
  const status=await fetch(backend+'/api/system/status',{signal:AbortSignal.timeout(15000),redirect:'error'})
  const runtime=status.ok?await status.json():{}
  if(!runtime.runtime_id||!runtime.build_id)throw new Error('Backend is not the expected MediGuide API; deployment configuration was not written.')
  const destination=fileURLToPath(new URL('../frontend/vercel.json',import.meta.url))
  await writeFile(destination,JSON.stringify(config,null,2)+'\n','utf8')
  console.log('Verified MediGuide backend and wrote frontend/vercel.json. Deploy with frontend as the Vercel project root.')
}

if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url){
  main().catch(error=>{console.error(error.message);process.exitCode=1})
}
