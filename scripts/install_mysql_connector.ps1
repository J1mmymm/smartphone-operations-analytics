[CmdletBinding()]
param(
    [string]$Installer = (Join-Path $env:TEMP "mysql-connector-net-9.5.0.msi")
)

$ErrorActionPreference = "Stop"
$statusFile = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")) "work\connector_helper_status.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $statusFile) | Out-Null
"started $(Get-Date -Format o)" | Set-Content -Encoding utf8 -LiteralPath $statusFile
if (-not (Test-Path -LiteralPath $Installer)) {
    "installer missing" | Add-Content -Encoding utf8 -LiteralPath $statusFile
    throw "Connector/NET installer not found: $Installer"
}

Write-Host "A Windows administrator prompt will open. Choose Yes to continue."
try {
    "requesting elevation" | Add-Content -Encoding utf8 -LiteralPath $statusFile
    $process = Start-Process msiexec.exe -Verb RunAs -ArgumentList @(
        "/i",
        $Installer,
        "/passive",
        "/norestart"
    ) -PassThru -Wait
}
catch {
    "elevation error: $($_.Exception.Message)" | Add-Content -Encoding utf8 -LiteralPath $statusFile
    throw
}

Write-Host "Installer exit code: $($process.ExitCode)"
"installer exit code: $($process.ExitCode)" | Add-Content -Encoding utf8 -LiteralPath $statusFile
if ($process.ExitCode -ne 0) {
    Write-Error "Connector/NET installation failed with exit code $($process.ExitCode)."
}
else {
    Write-Host "Connector/NET installation completed. Restart Power BI Desktop before refresh."
}
Read-Host "Press Enter to close"
