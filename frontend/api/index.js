// Project-level /api routing will send traffic to Render when it is live.
// Until then, fail explicitly rather than returning the SPA as an API response.
export default function handler(_request,response){
  response.setHeader('Content-Type','application/json; charset=utf-8')
  response.setHeader('Cache-Control','no-store')
  response.status(503).json({detail:'The medical backend deployment is not complete yet. Please finish the Render setup before signing in or asking medical questions.'})
}
