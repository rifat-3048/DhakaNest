#Requires -RunAsAdministrator
param([switch]$ApproveWindowsChanges)
$ErrorActionPreference = 'Stop'
if (-not $ApproveWindowsChanges) {
    throw 'Explicit approval is required for Windows feature/boot changes.'
}
$outputPath = Join-Path $PSScriptRoot 'approved_changes.json'
if (Test-Path -LiteralPath $outputPath) {
    throw 'A change record already exists; inspect it before repeating changes.'
}
$before = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
$record = [ordered]@{
    started_at_utc = [DateTime]::UtcNow.ToString('o')
    approval = 'Explicit user approval via execution permission; no reboot authorized'
    virtual_machine_platform_before = [string]$before.State
    attempted_actions = @()
    restart_performed = $false
    restart_required_before_docker_validation = $true
}
try {
    if ($before.State -eq 'Disabled') {
        $record.attempted_actions += 'Enable VirtualMachinePlatform with dependencies; NoRestart'
        $enabled = Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
        $record.feature_restart_needed = $enabled.RestartNeeded
    } elseif ([string]$before.State -notin @('Enabled', 'EnablePending')) {
        throw "Unexpected feature state: $($before.State)"
    }
    $record.attempted_actions += 'bcdedit /set hypervisorlaunchtype auto'
    $bootResult = & bcdedit.exe /set hypervisorlaunchtype auto
    if ($LASTEXITCODE -ne 0) { throw 'Boot configuration update failed.' }
    $record.boot_command_output = @($bootResult)
    $record.virtual_machine_platform_after = [string](Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform).State
    $bootLines = & bcdedit.exe /enum
    $record.hypervisor_launch_after = @($bootLines | Select-String -Pattern 'hypervisorlaunchtype' | ForEach-Object { $_.Line.Trim() })
    $record.status = 'Changes applied; restart and live verification still required'
} catch {
    $record.status = 'Failed or partial change; inspect actual state before retry'
    $record.error = $_.Exception.Message
    throw
} finally {
    $record.completed_at_utc = [DateTime]::UtcNow.ToString('o')
    $json = $record | ConvertTo-Json -Depth 6
    $stream = [System.IO.File]::Open($outputPath, [System.IO.FileMode]::CreateNew)
    try {
        $writer = New-Object System.IO.StreamWriter($stream, (New-Object System.Text.UTF8Encoding($false)))
        $writer.WriteLine($json)
        $writer.Flush()
    } finally {
        $stream.Dispose()
    }
}
