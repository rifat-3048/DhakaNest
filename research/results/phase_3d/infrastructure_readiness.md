# Infrastructure Readiness

Status: BLOCKED. Research-only implementation exists, but host virtualization/engine prerequisites prevent genuine local OSRM execution. No route measurements were manufactured.

Verified Windows 11 Pro amd64, Intel i5-1135G7, 4 physical cores/8 logical CPUs.
Total visible RAM 8148984 KiB (about 7.8 GiB);
free at inspection 1757820 KiB (about 1.7 GiB).
D: free 84140462080 bytes (about 78.4 GiB).
Docker CLI 28.0.4 and Compose v2.34.0-desktop.1 exist. Desktop Linux engine
named pipe is absent, including outside the sandbox. WSL defaults to Ubuntu,
version 2, but reports Virtual Machine Platform/BIOS virtualization prerequisites.
No native OSRM executable/process found. Port 5001 had no listener; a TIME_WAIT
entry does not reserve or prove future availability. Public documentation was
reachable; no extract download was attempted.

Administrator action needed: review/enable the Windows virtualization feature
and BIOS virtualization as appropriate, reboot if needed, then start existing
Docker Desktop/Linux engine. No such change was performed or authorized silently.
Review free memory before preparation. The 4-GiB-free/15-GiB-disk gates and
2-CPU/4-GiB container budgets are provisional safety choices, not measured
Bangladesh preprocessing requirements. Do not repeatedly launch OOM attempts.
Evidence: host_inspection.json; all initial access-denied system reads were
retried through explicit approved read-only escalation. Source tools: research/routing/osrm_local/. Data: benchmark_v1_3 reference overlay and its immutable benchmark_v1_2/v1_1 parents.
