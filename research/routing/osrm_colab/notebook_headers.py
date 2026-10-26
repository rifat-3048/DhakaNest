"""Versioned v9 notebook: preflight before native build, existing infrastructure retained."""

import ast
import json
from pathlib import Path
import pprint

from .notebook_sol2 import notebook as previous_notebook


def notebook():
    result = previous_notebook()
    result["metadata"]["colab"]["name"] = "DhakaNest_Phase3D_Colab_OSRM_v9.ipynb"
    for cell in result["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.startswith("CONFIG ="):
            config = ast.literal_eval(ast.parse(source).body[0].value)
            config.update(run_id="phase3d-colab-headers-001", local_root="/content/dhakanest_phase3d_headers",
                          repository_zip="/content/drive/MyDrive/DhakaNestResearch/dhakanest_colab_input_v9.zip",
                          authorize_native_build=False, native_retry_attempt=0, repair_only=True, authorize_runtime_smoke=False)
            source = "CONFIG = " + pprint.pformat(config, sort_dicts=False) + "\n"
        elif cell["cell_type"] == "code":
            source = source.replace("'research.routing.osrm_colab.native_build_v5'", "'research.routing.osrm_colab.native_build_v6'")
        elif cell["cell_type"] == "markdown" and source.startswith("# DhakaNest"):
            source = ("# DhakaNest Phase 3D: compiler-backed header preflight (v9)\n"
                      "Use v9 ZIP/checksum and a new CPU run ID/local root. Retain all v8\n"
                      "Python/APT/resource/authorization controls and exact warning scopes.\n"
                      "The upstream Git checkout stays pristine. A separate build-source copy\n"
                      "adds ONLY the justified vector include to suffix_table.hpp. No broad\n"
                      "forced-header list; the existing cstdint correction remains unchanged.\n\n"
                      "CMake File API selects the four-target dependency closure. Required\n"
                      "compiler probes and actual command audits must pass BEFORE full build.\n"
                      "Lexical candidates are not confirmed defects; new failures stop for\n"
                      "review rather than trigger automatic patches or expensive reruns.\n\n"
                      "Explicitly set authorize_native_build=True only when ready. Keep\n"
                      "repair_only=True and authorize_runtime_smoke=False. Run through setup\n"
                      "ONLY, then STOP; do not use Run all. No alternative binaries are\n"
                      "downloaded or selected. Native Linux OSRM success remains unverified.\n"
                      "See HEADERS_V9.md for limits, provenance, alternatives and instructions.\n")
        cell["source"] = source.splitlines(keepends=True)
    return result


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v9.ipynb"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(notebook(), stream, indent=2)
        stream.write("\n")
    print(path)
