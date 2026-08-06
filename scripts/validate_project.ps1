[CmdletBinding()]
param(
    [string]$LoginPath = "smartphone_analytics",
    [string]$MysqlExe = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$failures = [System.Collections.Generic.List[string]]::new()

Write-Host "[1/4] Checking deterministic data QA"
$qa = Get-Content -Raw -LiteralPath (Join-Path $repoRoot "data\quality\qa_report.json") | ConvertFrom-Json
if ($qa.overall_status -ne "PASS") {
    $failures.Add("data quality report is not PASS")
}

Write-Host "[2/4] Checking required deliverables"
$required = @(
    "excel\Smartphone_Operations_Analysis.xlsx",
    "powerbi\SmartphoneOperationsAnalytics.pbip",
    "powerbi\SmartphoneOperationsAnalytics.pbix",
    "powerbi\SmartphoneOperationsAnalytics.pdf",
    "powerbi\SmartphoneOperationsAnalytics.Report\definition\report.json",
    "powerbi\SmartphoneOperationsAnalytics.SemanticModel\definition\model.tmdl",
    "docs\powerbi_overview.png",
    "docs\powerbi_product_channel.png",
    "docs\powerbi_supply_cash.png",
    "docs\excel_dashboard.png",
    "README.md",
    "LICENSE"
)
foreach ($relative in $required) {
    $target = Join-Path $repoRoot $relative
    if (-not (Test-Path -LiteralPath $target)) {
        $failures.Add("missing deliverable: $relative")
    }
    elseif ((Get-Item -LiteralPath $target).PSIsContainer -eq $false -and (Get-Item -LiteralPath $target).Length -eq 0) {
        $failures.Add("empty deliverable: $relative")
    }
}

Write-Host "[3/4] Running MySQL quality checks"
if (Test-Path -LiteralPath $MysqlExe) {
    $sql = Get-Content -Raw -LiteralPath (Join-Path $repoRoot "sql\04_quality_checks.sql")
    $result = $sql | & $MysqlExe --login-path=$LoginPath --default-character-set=utf8mb4 --batch --raw
    if ($LASTEXITCODE -ne 0 -or ($result -match "FAIL")) {
        $failures.Add("MySQL quality checks failed")
    }
}
else {
    Write-Warning "MySQL client not found; database QA skipped."
}

Write-Host "[4/4] Validating PBIR"
$reportAuthor = Get-Command powerbi-report-author -ErrorAction SilentlyContinue
if ($reportAuthor) {
    & $reportAuthor.Source validate (Join-Path $repoRoot "powerbi\SmartphoneOperationsAnalytics.Report") --format text
    if ($LASTEXITCODE -ne 0) {
        $failures.Add("PBIR validation failed")
    }
}
else {
    Write-Warning "powerbi-report-author not found; PBIR validation skipped."
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Host "Project validation passed."
