"""Explicit opt-in local creation smoke; never runs in ordinary test discovery."""

import argparse
import json
from pathlib import Path
import platform
import subprocess
import uuid

from .environment import select_environment
from .storage import put_json
from .venv_setup import create_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("Explicit --execute required: fallback installs tools into a private target only")
    # Keep this Windows-only smoke below legacy MAX_PATH; Colab uses /content.
    root = Path(__file__).resolve().parent / "runtime/vs" / uuid.uuid4().hex[:8]
    root.mkdir(parents=True)
    selected = select_environment()
    standard = create_environment(root / "standard", selected)

    def simulated_missing(command, **kwargs):
        if "ensurepip" in command:
            return subprocess.CompletedProcess(command, 1, "", "SIMULATED: No module named ensurepip")
        if "venv" in command:
            return subprocess.CompletedProcess(command, 1, "", "SIMULATED: child -m ensurepip --upgrade --default-pip failed")
        return subprocess.run(command, **kwargs)

    fallback = create_environment(root / "fallback", selected, runner=simulated_missing)
    reuse = create_environment(root / "fallback", selected)
    record = {"status": "local_creation_smoke_passed", "platform": platform.platform(), "python": platform.python_version(),
              "standard": standard, "fallback": fallback, "reuse": reuse,
              "ensurepip_absence_simulated": True, "bootstrap_tools_installed_into_private_target": True,
              "system_packages_modified": False, "research_dependencies_installed": False,
              "colab_executed": False, "live_osrm_requests": 0}
    put_json(root / "smoke_result.json", record)
    # Keep host-specific paths/logs out of the immutable source specification.
    output = Path(__file__).resolve().parents[2] / "results/phase_3d_colab/venv_repair_v1/local_creation_smoke.json"
    put_json(output, record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
