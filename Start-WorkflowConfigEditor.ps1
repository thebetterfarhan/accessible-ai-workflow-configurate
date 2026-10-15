$app = Join-Path $PSScriptRoot 'dist\AccessibleAIWorkflowConfigurate.exe'
if (-not (Test-Path -LiteralPath $app)) {
    throw "Build missing: $app"
}
Start-Process -FilePath $app
