$ErrorActionPreference = 'Stop'
Set-Location (Join-Path (Split-Path $PSScriptRoot -Parent) 'frontend')
if (Get-Command npm -ErrorAction SilentlyContinue) {
    npm run dev
} else {
    node ..\.tools\package\bin\npm-cli.js run dev
}
