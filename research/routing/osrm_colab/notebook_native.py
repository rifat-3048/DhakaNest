"""Generate v5 while preserving the v4 notebook and environment setup."""

import ast
import json
from pathlib import Path
import pprint

from .notebook_venv import notebook as previous_notebook


def notebook():
    result = previous_notebook()
    result["metadata"]["colab"]["name"] = "DhakaNest_Phase3D_Colab_OSRM_v5.ipynb"
    for cell in result["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.startswith("CONFIG ="):
            config = ast.literal_eval(ast.parse(source).body[0].value)
            config.update(run_id="phase3d-colab-native-v2-001", local_root="/content/dhakanest_phase3d_native_v2",
                          repository_zip="/content/drive/MyDrive/DhakaNestResearch/dhakanest_colab_input_v5.zip",
                          authorize_native_build=False, native_retry_attempt=0, repair_only=True)
            source = "CONFIG = " + pprint.pformat(config, sort_dicts=False) + "\n"
        elif cell["cell_type"] == "code" and "install_dependencies.sh" in source:
            source = "# Explicit authorization is checked before package installation or compilation.\nstage('setup')\n"
        elif cell["cell_type"] == "code":
            source = source.replace("research.routing.osrm_colab.workflow", "research.routing.osrm_colab.native_build")
        elif cell["cell_type"] == "markdown" and source.startswith("## 5."):
            source = ("## 5. Explicitly authorized clean native build\n"
                      "Set authorize_native_build=True in CONFIG and rerun the configuration/setup\n"
                      "cells to authorize installation and compilation. A fresh CPU runtime avoids\n"
                      "conflicting preinstalled Boost development packages; apt refuses removals.\n"
                      "STOP after this stage during the repair. Full logs and first diagnostics\n"
                      "persist in Drive, including on failure. See NATIVE_BUILD_REPAIR.md.\n")
        elif cell["cell_type"] == "markdown" and source.startswith("# DhakaNest"):
            source += "\n## Native build revision (v5)\nUse a fresh Ubuntu 22.04/24.04 x86_64 CPU runtime and the v5 ZIP.\nGCC 11, Boost 1.74 and a serial clean build retain official OSRM v5.27.1.\nThis configuration has NOT yet been compiled in Colab. The original earliest\ncompiler diagnostic is not available, so its root cause is not confirmed.\nSet authorize_native_build=True only when ready to install packages and build.\nKeep repair_only=True and STOP after setup for this repair. Later download,\npreprocess and acquisition cells deliberately refuse execution in repair mode.\nDo not delete old logs or failed-stage records. Read NATIVE_BUILD_REPAIR.md\nfor exact-attempt retry authorization. No retries are automatic.\n"
        cell["source"] = source.splitlines(keepends=True)
    return result


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v5.ipynb"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(notebook(), stream, indent=2)
        stream.write("\n")
    print(path)
