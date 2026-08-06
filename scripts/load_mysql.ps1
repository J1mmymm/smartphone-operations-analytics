[CmdletBinding()]
param(
    [string]$LoginPath = "smartphone_analytics",
    [string]$MysqlExe = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path -LiteralPath $MysqlExe)) {
    throw "MySQL client was not found at: $MysqlExe"
}

$sqlFiles = @(
    "sql/00_create_database.sql",
    "sql/01_create_tables.sql",
    "sql/02_load_data.sql",
    "sql/03_create_views.sql"
)

$previousLocation = Get-Location
try {
    Set-Location -LiteralPath $repoRoot
    foreach ($file in $sqlFiles) {
        Write-Host "Running $file"
        Get-Content -Raw -LiteralPath $file | & $MysqlExe --login-path=$LoginPath --local-infile=1 --default-character-set=utf8mb4 --show-warnings
        if ($LASTEXITCODE -ne 0) {
            throw "MySQL execution failed for $file"
        }
    }
    Write-Host "Database load completed: nanhu_mobile_analytics"
}
finally {
    Set-Location -LiteralPath $previousLocation
}
