#Requires -RunAsAdministrator
# Read-only host diagnostics. The only write is a new research evidence file.
$ErrorActionPreference = 'Stop'
$outputPath = Join-Path $PSScriptRoot 'administrator_diagnostics.json'
if (Test-Path -LiteralPath $outputPath) {
    throw 'Evidence already exists. Preserve it and use a new versioned path.'
}

$features = foreach ($name in @('VirtualMachinePlatform', 'Microsoft-Windows-Subsystem-Linux', 'Microsoft-Hyper-V-All')) {
    $feature = Get-WindowsOptionalFeature -Online -FeatureName $name
    [ordered]@{ name = $name; state = [string]$feature.State }
}
$bootLines = & bcdedit.exe /enum
if ($LASTEXITCODE -ne 0) { throw 'Read-only BCD inspection failed.' }
$launch = @($bootLines | Select-String -Pattern 'hypervisorlaunchtype' | ForEach-Object { $_.Line.Trim() })
$processor = Get-CimInstance Win32_Processor | Select-Object -First 1
$computer = Get-CimInstance Win32_ComputerSystem
$record = [ordered]@{
    checked_at_utc = [DateTime]::UtcNow.ToString('o')
    features = @($features)
    hypervisor_launch_entries = $launch
    launch_entry_absent_means = 'Not explicitly shown; do not infer disabled from absence.'
    virtualization_firmware_enabled = $processor.VirtualizationFirmwareEnabled
    vm_monitor_mode_extensions = $processor.VMMonitorModeExtensions
    second_level_address_translation = $processor.SecondLevelAddressTranslationExtensions
    hypervisor_present = $computer.HypervisorPresent
    system_settings_changed = $false
}
$json = $record | ConvertTo-Json -Depth 6
$stream = [System.IO.File]::Open($outputPath, [System.IO.FileMode]::CreateNew)
try {
    $writer = New-Object System.IO.StreamWriter($stream, (New-Object System.Text.UTF8Encoding($false)))
    $writer.WriteLine($json)
    $writer.Flush()
} finally {
    $stream.Dispose()
}
