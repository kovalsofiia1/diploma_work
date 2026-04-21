param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "== Hardhat local bootstrap ==" -ForegroundColor Cyan
Write-Host "Project: $scriptDir"

if (-not $SkipInstall -and -not (Test-Path "$scriptDir/node_modules")) {
    Write-Host "`nInstalling npm dependencies..." -ForegroundColor Yellow
    & npm.cmd install
}

Write-Host "`nStarting Hardhat node in a new window..." -ForegroundColor Yellow
$nodeCmd = "cd /d `"$scriptDir`" && npx hardhat node"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $nodeCmd | Out-Null

Write-Host "Waiting for RPC http://127.0.0.1:8545 ..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $null = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8545" -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' -TimeoutSec 2
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $ready) {
    throw "Hardhat RPC did not start in time. Check the opened node window for errors."
}

Write-Host "`nDeploying TicketRegistry to localhost..." -ForegroundColor Yellow
$deployOutput = & npx.cmd hardhat run scripts/deploy.cjs --network localhost 2>&1
$deployOutput | ForEach-Object { Write-Host $_ }

$addressLine = $deployOutput | Where-Object { $_ -match "TICKET_CONTRACT_ADDRESS=" } | Select-Object -First 1
$contractAddress = $null
if ($addressLine) {
    $parts = $addressLine -split "=", 2
    if ($parts.Count -eq 2) {
        $contractAddress = $parts[1].Trim()
    }
}

Write-Host "`n== Done ==" -ForegroundColor Green
if ($contractAddress) {
    Write-Host "Contract address: $contractAddress" -ForegroundColor Green
    Write-Host ""
    Write-Host "Set backend .env values:" -ForegroundColor Cyan
    Write-Host "ETHEREUM_RPC_URL=http://127.0.0.1:8545"
    Write-Host "TICKET_CONTRACT_ADDRESS=$contractAddress"
    Write-Host ""
    Write-Host "Then restart backend."
} else {
    Write-Host "Contract deployed, but address was not parsed automatically." -ForegroundColor Yellow
    Write-Host "Look for line: TICKET_CONTRACT_ADDRESS=..."
}

