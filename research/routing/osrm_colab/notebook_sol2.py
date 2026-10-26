"""Versioned v8 notebook; all v7 cells/artifacts remain preserved on disk."""

import ast
import json
from pathlib import Path
import pprint

from .notebook_compatibility import notebook as previous_notebook


def notebook():
    result = previous_notebook()
    result["metadata"]["colab"]["name"] = "DhakaNest_Phase3D_Colab_OSRM_v8.ipynb"
    for cell in result["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.startswith("CONFIG ="):
            config = ast.literal_eval(ast.parse(source).body[0].value)
            config.update(run_id="phase3d-colab-sol2-001", local_root="/content/dhakanest_phase3d_sol2",
                          repository_zip="/content/drive/MyDrive/DhakaNestResearch/dhakanest_colab_input_v8.zip",
                          authorize_native_build=False, native_retry_attempt=0, repair_only=True,
                          authorize_runtime_smoke=False)
            source = "CONFIG = " + pprint.pformat(config, sort_dicts=False) + "\n"
        elif cell["cell_type"] == "code":
            source = source.replace("'research.routing.osrm_colab.native_build_v4'",
                                    "'research.routing.osrm_colab.native_build_v5'")
        elif cell["cell_type"] == "markdown" and source.startswith("# DhakaNest"):
            source = ("# DhakaNest Phase 3D: targeted Sol2 repair (v8)\n"
                      "Use a CPU runtime, v8 ZIP/checksum and the new default run ID/local root.\n"
                      "Original OSRM/Sol2 source remains pristine. GNU bounds warnings become\n"
                      "nonfatal ONLY in scripting_environment_lua.cpp; keep them visible.\n"
                      "Retain global Werror, GCC-11/osrm.cpp exception and cstdint correction.\n"
                      "Exported C++ commands must prove the exact scopes before compilation.\n\n"
                      "The warning's harmlessness is not proven. No local Linux build or\n"
                      "runtime smoke success is claimed. Bulk acquisition is blocked in v8,\n"
                      "even after changing repair_only. Runtime smoke needs separate explicit\n"
                      "authorization for extraction, preprocessing, server and Table validation.\n\n"
                      "Explicitly set authorize_native_build=True to permit setup. Keep\n"
                      "repair_only=True and authorize_runtime_smoke=False for this repair.\n"
                      "Run through setup ONLY, then STOP. Do not use Run all. Read SOL2_V8.md.\n")
        cell["source"] = source.splitlines(keepends=True)
    return result


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v8.ipynb"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(notebook(), stream, indent=2)
        stream.write("\n")
    print(path)
