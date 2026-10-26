# Phase 3D Recovery: Restart Required

Status: **targeted Windows corrections applied with approval; recovery awaits a
user-controlled restart and live Docker/OSRM verification**. This continues Phase
3D, not a new phase. No earlier code, reports, data or manifests were replaced.

## Verified Diagnosis

Read-only CIM checks confirm CPU virtualization extensions, second-level address
translation and firmware virtualization are all enabled. HypervisorPresent was
false. Therefore a BIOS change is not indicated by the current evidence.

Ordinary tools outside the sandbox could not read Windows feature/BCD state:
they lacked Windows administrator rights, which differ from sandbox escalation.
A separately approved UAC elevation ran diagnose_windows.ps1, which changes no
system settings. It established:

| Setting | Before correction |
|---|---|
| VirtualMachinePlatform | Disabled |
| Microsoft-Windows-Subsystem-Linux | Enabled |
| Microsoft-Hyper-V-All | Disabled |
| hypervisorlaunchtype | Off |
| Firmware virtualization | Enabled |
| Windows hypervisor running | False |

These are concrete blockers to the WSL2-backed Linux engine. Full Hyper-V is not
being enabled as a generic remedy. WSL 2.4.13.0 and its kernel 5.15.167.4-1 are
installed; Ubuntu and docker-desktop distributions were stopped, both version 2.
No WSL/Docker installation, update or distribution replacement was performed.

## Corrections Performed

First attempted the permitted normal user-level startup of existing Docker
Desktop. Its processes started, but docker version still returned no server
and an EOF against dockerDesktopLinuxEngine. Startup alone did not fix the VM
prerequisites. No backend switching or unrelated Docker resource removal occurred.

After explicit execution approval and Windows UAC approval, ran only:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
bcdedit /set hypervisorlaunchtype auto
```

The result was verified within the elevated helper: VirtualMachinePlatform is
**EnablePending**, hypervisorlaunchtype is **Auto**, and RestartNeeded is true.
No restart was performed. The changes can affect other virtualization software;
they were not silently applied or described as proof the engine now works.
The helper records partial failures too and refuses accidental repetition after
a change record exists.

Evidence, preserved without overwriting:

- research/routing/osrm_local/recovery/administrator_diagnostics.json
- research/routing/osrm_local/recovery/approved_changes.json
- Adjacent diagnose_windows.ps1 and enable_virtualization.ps1 source files.

## Remaining Actions and Resources

1. User saves work and restarts Windows voluntarily. No automatic restart or
   additional boot/firmware change is authorized by this recovery operation.
2. Open existing Docker Desktop after restart and wait for the Linux engine.
3. Verify with the read-only commands below. HypervisorPresent should become
   true, WSL should no longer report the prerequisite error, and docker version
   should include a Linux Server section. If not, inspect the actual errors
   before proposing any additional system changes.

```powershell
Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent
wsl --status
docker version
```

Rechecked disk: D: free 84,140,146,688 bytes (about 78.4 GiB). Memory at the
recovery inspection was 1,725,344 KiB free out of 8,148,984 KiB (roughly 1.6/7.8
GiB). This is not an adequate basis to start the existing provisional 4-GiB-free
preparation gate. Recheck after reboot and review resources before heavy work;
the safety gates are not measured full-country preprocessing requirements.

No OSM extract or OSRM image was downloaded. Actual PBF checksum, installed OSRM
version, preprocessing resource use and real smoke results remain unavailable.
The existing Geofabrik Bangladesh/MLD/car plan is unchanged. Significant image,
extract or storage commitments still need approval and current size checks.
If the full country proves infeasible, a smaller connected extract requires an
explicitly reviewed dataset decision, not a silent substitution.

## Benchmark and Non-Regression

Local/public bulk routing requests=0. Genuine measurements=0, supported
unreachable=0, failed route requests=0, missing logical/physical pairs=30,000.
No missing measurement was converted to a zero or unreachable route.
Post-commute candidate bins and profiles with >=10 feasible homes remain
unknown. All original profiles/thresholds and the 60/140 split remain unchanged.
The 4,800 blinded/unlabeled pairs remain provisional; Phase 4 is not ready.

Actually reran 137 research tests and 104 backend recommendation/inventory
regressions: all passed, no skips reported. Both new PowerShell helpers passed
PowerShell parser checks. Prior Phase 3D seal verified 26 output hashes, plus
Phase 3C=30, Phase 3B=52, Phase 3A=51 and Phase 0-2=44. Tracked git diff is empty.
Production source, MongoDB and model/assessment files were not modified or
accessed for recovery. The approved Windows feature/boot changes and normal
Docker Desktop startup are the only host corrections made. No ranking metrics,
baselines, ablations, annotation, deployment or new research framework was added.

Next execution resumes existing operator.py register/prepare/start/smoke/acquire
only after reboot, engine verification, resource checks and download approval.
The prior blocked benchmark remains historical evidence; a genuine completed
matrix must use a new versioned acquired overlay, not overwrite old snapshots.

Technical guidance consulted:
[Microsoft WSL troubleshooting](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting),
[Docker virtualization troubleshooting](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/topics/).
