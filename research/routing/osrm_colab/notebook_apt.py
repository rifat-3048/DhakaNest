"""Generate v6 without changing the historical v5 notebook or archive."""

import ast
import json
from pathlib import Path
import pprint

from .notebook_native import notebook as previous_notebook


def notebook():
    result = previous_notebook()
    result["metadata"]["colab"]["name"] = "DhakaNest_Phase3D_Colab_OSRM_v6.ipynb"
    for cell in result["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.startswith("CONFIG ="):
            config = ast.literal_eval(ast.parse(source).body[0].value)
            config.update(run_id="phase3d-colab-additive-apt-001", local_root="/content/dhakanest_phase3d_apt_v3",
                          repository_zip="/content/drive/MyDrive/DhakaNestResearch/dhakanest_colab_input_v6.zip",
                          authorize_native_build=False, native_retry_attempt=0, repair_only=True)
            source = "CONFIG = " + pprint.pformat(config, sort_dicts=False) + "\n"
        elif cell["cell_type"] == "code":
            # Guard/config functions live in workflow, not the native build wrappers.
            source = source.replace("from research.routing.osrm_colab.native_build import",
                                    "from research.routing.osrm_colab.workflow import")
            source = source.replace("'research.routing.osrm_colab.native_build'",
                                    "'research.routing.osrm_colab.native_build_v3'")
        elif cell["cell_type"] == "markdown" and source.startswith("# DhakaNest"):
            source = ("# DhakaNest Phase 3D: additive APT repair (v6)\n"
                      "Select a CPU runtime on Ubuntu 22.04/24.04 x86_64 and mount Drive.\n"
                      "Use the v6 ZIP and enter its exact SHA-256 in CONFIG. Historical runs\n"
                      "and archives stay unchanged. No production or methodology changes.\n\n"
                      "The confirmed v5 failure was an APT conflict, not compilation. V6 keeps\n"
                      "installed Boost (1.83 in the affected runtime), tries the existing GNU\n"
                      "compiler first and validates probes before accepting any build. No Linux\n"
                      "APT simulation or native compilation was executed during local repair.\n\n"
                      "Set authorize_native_build=True only to authorize installation/build.\n"
                      "Keep repair_only=True. Run through setup and STOP. Later map/routing\n"
                      "stages deliberately refuse execution. See APT_REPAIR_V6.md for logs\n"
                      "and exact-attempt retry instructions. Do not use Run all for this repair.\n")
        elif cell["cell_type"] == "markdown" and source.startswith("## 5."):
            source = ("## 5. Explicitly authorized, additive-only setup\n"
                      "Detect installed Boost/compiler/libraries. Simulate APT before every\n"
                      "install; reject removals, upgrades, downgrades and unresolved conflicts.\n"
                      "Retain installed Boost, prefer the current compiler if the unmodified\n"
                      "OSRM header probe passes, and conditionally try GCC 11 otherwise.\n"
                      "Full logs, both simulation passes, package inventories, probes and\n"
                      "first-error summaries persist to Drive. STOP after this stage.\n")
        cell["source"] = source.splitlines(keepends=True)
    return result


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v6.ipynb"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(notebook(), stream, indent=2)
        stream.write("\n")
    print(path)
