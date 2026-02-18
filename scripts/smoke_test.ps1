$ErrorActionPreference = "Stop"

& "$PSScriptRoot\check_docker.ps1"

try { chcp 65001 | Out-Null } catch {}
$OutputEncoding = [System.Text.Encoding]::UTF8
try {
  [Console]::InputEncoding = [System.Text.Encoding]::UTF8
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

$core = "http://127.0.0.1:8000"
$agent = "http://127.0.0.1:8001"
$rag = "http://127.0.0.1:8003"

function Invoke-WebJsonUtf8 {
  param(
    [Parameter(Mandatory = $true)][ValidateSet("GET","POST","PUT","PATCH","DELETE")][string]$Method,
    [Parameter(Mandatory = $true)][string]$Uri,
    [Parameter(Mandatory = $false)][byte[]]$BodyBytes,
    [Parameter(Mandatory = $false)][string]$ContentType
  )

  $params = @{
    Proxy = $null
    Method = $Method
    Uri = $Uri
    Headers = @{ Accept = "application/json" }
    TimeoutSec = 15
    UseBasicParsing = $true
  }
  if ($null -ne $BodyBytes) {
    $params["Body"] = $BodyBytes
    $params["ContentType"] = $ContentType
  }

  $resp = Invoke-WebRequest @params
  $ms = New-Object System.IO.MemoryStream
  $resp.RawContentStream.CopyTo($ms)
  $text = [System.Text.Encoding]::UTF8.GetString($ms.ToArray())
  if (-not $text) { return $null }
  return $text | ConvertFrom-Json
}

function Invoke-PostJsonUtf8 {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [Parameter(Mandatory = $true)]$Object
  )
  $json = $Object | ConvertTo-Json -Depth 20
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  return Invoke-WebJsonUtf8 -Method "POST" -Uri $Uri -BodyBytes $bytes -ContentType "application/json; charset=utf-8"
}

function Invoke-CurlMultipartJson {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [Parameter(Mandatory = $true)][string[]]$FormParts
  )

  $args = @("-sS", "--noproxy", "*", "-X", "POST", $Uri)
  foreach ($p in $FormParts) { $args += @("-F", $p) }
  $out = & curl.exe @args
  if ($LASTEXITCODE -ne 0) { throw "curl.exe failed with exit code $LASTEXITCODE" }
  if (-not $out) { return $null }
  return $out | ConvertFrom-Json
}

function Wait-Ok {
  param([string]$Url, [int]$TimeoutSec = 120)
  $start = Get-Date
  while ($true) {
    try {
      $r = Invoke-WebJsonUtf8 -Method "GET" -Uri $Url
      if ($r -and $r.ok -eq $true) { return }
    } catch {}
    if (((Get-Date) - $start).TotalSeconds -gt $TimeoutSec) {
      throw "Timeout waiting for $Url"
    }
    Start-Sleep -Seconds 2
  }
}

Write-Host "0) docker compose up -d --build"
& docker compose up -d --build | Out-Null

Write-Host "1) wait health"
Wait-Ok "$core/health" 180
Wait-Ok "$agent/health" 180
Wait-Ok "$rag/health" 180

Write-Host "2) agent: create lead + draft estimate"
$resp = Invoke-PostJsonUtf8 -Uri "$agent/api/agent/message" -Object @{
  channel = "web"
  # Keep this ASCII-only to avoid encoding issues in Windows PowerShell 5.1 script parsing.
  message = "Need oil service for Kia Rio 2017 mileage 120k"
}
if (-not $resp.lead_id) { throw "No lead_id returned" }
$leadId = $resp.lead_id
Write-Host "lead_id=$leadId"

Write-Host "3) check estimate exists"
$estimateId = $null
try { $estimateId = $resp.draft_estimate.id } catch {}
if (-not $estimateId) {
  # be resilient to eventual consistency / startup load
  $start = Get-Date
  while (-not $estimateId) {
    $estimates = Invoke-WebJsonUtf8 -Method "GET" -Uri "$core/api/estimates?lead_id=$leadId"
    if ($estimates -and $estimates.Count -ge 1) { $estimateId = $estimates[0].id }
    if ($estimateId) { break }
    if (((Get-Date) - $start).TotalSeconds -gt 30) { throw "No estimates for lead" }
    Start-Sleep -Seconds 2
  }
}
Write-Host "estimate_id=$estimateId"

Write-Host "4) approve estimate"
$approved = Invoke-PostJsonUtf8 -Uri "$core/api/estimate/$estimateId/approve" -Object @{ approved_by = "smoke" }
if ($approved.requires_approval -ne $false) { throw "Approve failed" }

Write-Host "5) suppliers present (seed)"
$suppliers = Invoke-WebJsonUtf8 -Method "GET" -Uri "$core/api/suppliers"
if (-not $suppliers -or -not $suppliers[0].id) { throw "No suppliers found (seed failed?)" }
$supplierId = $suppliers[0].id
Write-Host "supplier_id=$supplierId"

Write-Host "6) import supplier CSV"
$csvPath = (Resolve-Path (Join-Path $PSScriptRoot "..\demo-data\suppliers\demo.csv")).Path
$import = Invoke-CurlMultipartJson -Uri "$core/api/suppliers/import" -FormParts @(
  ("supplier_id={0}" -f $supplierId),
  ("file=@`"{0}`"" -f $csvPath)
)
if (-not $import.imported) { throw "CSV import failed" }

Write-Host "7) compare part offers"
$cmp = Invoke-WebJsonUtf8 -Method "GET" -Uri "$core/api/parts/compare?oem=04465-33480"
if (-not $cmp -or $cmp.Count -lt 1) { throw "Compare returned empty list" }

Write-Host "8) upload + query RAG"
$docPath = (Resolve-Path (Join-Path $PSScriptRoot "..\demo-data\docs\to_reglament.md")).Path
$up = Invoke-CurlMultipartJson -Uri "$core/api/documents/upload" -FormParts @(
  ("file=@`"{0}`"" -f $docPath)
)
if (-not $up.document_id) { throw "Doc upload failed" }
$ragQuery = Invoke-PostJsonUtf8 -Uri "$rag/api/rag/query" -Object @{ query = "oil filter"; top_k = 2 }
if (-not $ragQuery.results -or $ragQuery.results.Count -lt 1) { throw "RAG query returned empty" }

Write-Host "9) DB checks (simple counts)"
$q1 = "SELECT count(*) FROM leads;"
$q2 = "SELECT count(*) FROM estimates;"
$q3 = "SELECT count(*) FROM supplier_offers;"
$q4 = "SELECT count(*) FROM documents;"
$counts = @{}
foreach ($q in @($q1,$q2,$q3,$q4)) {
  $out = & docker compose exec -T postgres psql -U autoshop -d autoshop -t -A -c $q
  $counts[$q] = [int]($out.Trim())
}
if ($counts[$q1] -lt 1) { throw "DB leads count < 1" }
if ($counts[$q2] -lt 1) { throw "DB estimates count < 1" }
if ($counts[$q3] -lt 50) { throw "DB supplier_offers count < 50" }
if ($counts[$q4] -lt 1) { throw "DB documents count < 1" }

Write-Host "SMOKE OK"

