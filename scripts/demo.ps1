$ErrorActionPreference = "Stop"

& "$PSScriptRoot\check_docker.ps1"

# Make Cyrillic output readable in Windows PowerShell console.
try { chcp 65001 | Out-Null } catch {}
$OutputEncoding = [System.Text.Encoding]::UTF8
try {
  [Console]::InputEncoding = [System.Text.Encoding]::UTF8
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

function Utf8FromB64 {
  param([Parameter(Mandatory = $true)][string]$B64)
  return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($B64))
}

$msgMaintenance = Utf8FromB64 "0J3Rg9C20L3QviDQotCeINC90LAgS2lhIFJpbyAyMDE3LCDQv9GA0L7QsdC10LMgMTIw0Lo="
$msgParts = Utf8FromB64 "0J3Rg9C20L3RiyDQutC+0LvQvtC00LrQuCDQvdCwIENhbXJ5IDUw"

# Use 127.0.0.1 to avoid proxy/DNS issues with "localhost" on some corp setups.
$core = "http://127.0.0.1:8000"
$agent = "http://127.0.0.1:8001"
$rag = "http://127.0.0.1:8003"

function Invoke-PostJsonUtf8 {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [Parameter(Mandatory = $true)]$Object
  )

  $json = $Object | ConvertTo-Json -Depth 20
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  return Invoke-WebJsonUtf8 -Method "POST" -Uri $Uri -BodyBytes $bytes -ContentType "application/json; charset=utf-8"
}

function Invoke-WebJsonUtf8 {
  param(
    [Parameter(Mandatory = $true)][ValidateSet("GET","POST","PUT","PATCH","DELETE")][string]$Method,
    [Parameter(Mandatory = $true)][string]$Uri,
    [Parameter(Mandatory = $false)][byte[]]$BodyBytes,
    [Parameter(Mandatory = $false)][string]$ContentType
  )

  $params = @{
    Proxy = $null
    UseBasicParsing = $true
    TimeoutSec = 30
    Method = $Method
    Uri = $Uri
    Headers = @{ Accept = "application/json" }
  }
  if ($null -ne $BodyBytes) {
    $params["Body"] = $BodyBytes
    $params["ContentType"] = $ContentType
  }

  $resp = Invoke-WebRequest @params

  # Always decode as UTF-8 to avoid mojibake in Windows PowerShell 5.1.
  $ms = New-Object System.IO.MemoryStream
  $resp.RawContentStream.CopyTo($ms)
  $text = [System.Text.Encoding]::UTF8.GetString($ms.ToArray())
  if (-not $text) { return $null }
  return $text | ConvertFrom-Json
}

function Invoke-CurlMultipartJson {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [Parameter(Mandatory = $true)][string[]]$FormParts
  )

  $args = @("-sS", "--noproxy", "*", "-X", "POST", $Uri)
  foreach ($p in $FormParts) {
    $args += @("-F", $p)
  }

  $out = & curl.exe @args
  if ($LASTEXITCODE -ne 0) {
    throw "curl.exe failed with exit code $LASTEXITCODE"
  }
  if (-not $out) { return $null }
  return $out | ConvertFrom-Json
}

Write-Host "1) Agent message (maintenance)"
$resp = Invoke-PostJsonUtf8 -Uri "$agent/api/agent/message" -Object @{
  channel = "web"
  message = $msgMaintenance
}
$leadId = $resp.lead_id
Write-Host "lead_id=$leadId"

Write-Host "2) Suppliers"
$suppliers = Invoke-WebJsonUtf8 -Method "GET" -Uri "$core/api/suppliers"
if (-not $suppliers -or -not $suppliers[0].id) { throw "No suppliers found (seed failed?)" }
$supplierId = $suppliers[0].id
Write-Host "supplier_id=$supplierId"

Write-Host "2b) Upload demo RAG document"
$docs = @(
  (Join-Path $PSScriptRoot "..\demo-data\reglament_to.txt"),
  (Join-Path $PSScriptRoot "..\demo-data\docs\to_reglament.md"),
  (Join-Path $PSScriptRoot "..\demo-data\docs\suspension_symptoms.md")
)
foreach ($p in $docs) {
  $ragFile = (Resolve-Path $p).Path
  $ragResp = Invoke-CurlMultipartJson -Uri "$rag/api/rag/upload" -FormParts @(
    ("file=@`"{0}`"" -f $ragFile)
  )
  Write-Host ("uploaded=" + (Split-Path $p -Leaf) + " chunks=" + $ragResp.chunks)
}

Write-Host "3) Import price CSV"
$filePath = Join-Path $PSScriptRoot "..\demo-data\suppliers\demo.csv"
$csv = (Resolve-Path $filePath).Path
$import = Invoke-CurlMultipartJson -Uri "$core/api/suppliers/import" -FormParts @(
  ("supplier_id={0}" -f $supplierId),
  ("file=@`"{0}`"" -f $csv)
)
Write-Host ("imported=" + $import.imported)

Write-Host "3b) Import price XLSX (optional)"
$xlsxPath = Join-Path $PSScriptRoot "..\demo-data\supplier_price.xlsx"
$xlsx = (Resolve-Path $xlsxPath).Path
$importX = Invoke-CurlMultipartJson -Uri "$core/api/suppliers/import" -FormParts @(
  ("supplier_id={0}" -f $supplierId),
  ("file=@`"{0}`"" -f $xlsx)
)
Write-Host ("imported_xlsx=" + $importX.imported)

Write-Host "4) Parts scenario via agent"
$resp2 = Invoke-PostJsonUtf8 -Uri "$agent/api/agent/message" -Object @{
  channel = "web"
  message = $msgParts
}
Write-Host $resp2.answer

Write-Host "5) Compare offers"
$cmp = Invoke-WebJsonUtf8 -Method "GET" -Uri "$core/api/parts/compare?oem=04465-33480"
$cmp | ConvertTo-Json -Depth 6

Write-Host "6) Check logs (agent_runs)"
$runs = Invoke-WebJsonUtf8 -Method "GET" -Uri "$core/api/agent_runs?lead_id=$leadId"
$runs | Select-Object -First 1 | ConvertTo-Json -Depth 10

