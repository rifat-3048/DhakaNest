"""Generate v7 without rewriting the v6 notebook or its research evidence."""

import ast
import json
from pathlib import Path
import pprint

from .notebook_apt import notebook as previous_notebook


def notebook():
    result = previous_notebook()
    result["metadata"]["colab"]["name"] = "DhakaNest_Phase3D_Colab_OSRM_v7.ipynb"
    for cell in result["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.startswith("CONFIG ="):
            config = ast.literal_eval(ast.parse(source).body[0].value)
            config.update(run_id="phase3d-colab-cstdint-001", local_root="/content/dhakanest_phase3d_cstdint",
                          repository_zip="/content/drive/MyDrive/DhakaNestResearch/dhakanest_colab_input_v7.zip",
                          authorize_native_build=False, native_retry_attempt=0, repair_only=True)
            source = "CONFIG = " + pprint.pformat(config, sort_dicts=False) + "\n"
        elif cell["cell_type"] == "code":
            source = source.replace("'research.routing.osrm_colab.native_build_v3'",
                                    "'research.routing.osrm_colab.native_build_v4'")
        elif cell["cell_type"] == "markdown" and source.startswith("# DhakaNest"):
            source = ("# DhakaNest Phase 3D: cstdint compatibility (v7)\n"
                      "CPU only. Keep the v6 additive APT strategy and installed Boost.\n"
                      "Use v7 ZIP/checksum and a new run ID/local root. All previous versions\n"
                      "and failure evidence remain unchanged. No local Linux build is claimed.\n\n"
                      "Compare the original coordinate header, a disposable one-line cstdint\n"
                      "patch, and a build-only forced include. The build uses pristine source\n"
                      "with recorded -include cstdint. Global Werror stays enabled. For GCC 11\n"
                      "only, free-nonheap-object is a visible warning only in src/osrm/osrm.cpp,\n"
                      "matching the supplied routed failure. No broader demotion is permitted.\n\n"
                      "Set authorize_native_build=True explicitly; keep repair_only=True.\n"
                      "Run only through setup, then STOP. Do not use Run all or acquire routing.\n"
                      "See COMPATIBILITY_V7.md for evidence, limitations and retry instructions.\n")
        elif cell["cell_type"] == "markdown" and source.startswith("## 5."):
            source = ("## 5. Authorized compatibility comparison and clean build\n"
                      "Exact commands, source/patch/override hashes, all compiler diagnostics\n"
                      "and separate probe/build warning summaries are saved to Drive.\n"
                      "All four tools must compile and validate before setup is accepted.\n"
                      "No global warning suppression or automatic expensive retry is enabled.\n")
        cell["source"] = source.splitlines(keepends=True)
    return result


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v7.ipynb"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(notebook(), stream, indent=2)
        stream.write("\n")
    print(path)
