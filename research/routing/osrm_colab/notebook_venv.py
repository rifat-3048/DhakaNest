"""Create v4 without modifying any earlier notebook or its generator."""

import ast
import json
from pathlib import Path
import pprint
import textwrap

from .notebook_compat import notebook as previous_notebook


def notebook():
    result = previous_notebook()
    result["metadata"]["colab"]["name"] = "DhakaNest_Phase3D_Colab_OSRM_v4.ipynb"
    for cell in result["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.startswith("CONFIG ="):
            config = ast.literal_eval(ast.parse(source).body[0].value)
            config.update(run_id="phase3d-colab-venv-001", local_root="/content/dhakanest_phase3d_venv",
                          repository_zip="/content/drive/MyDrive/DhakaNestResearch/dhakanest_colab_input_v4.zip")
            source = "CONFIG = " + pprint.pformat(config, sort_dicts=False) + "\n"
        elif cell["cell_type"] == "code" and "config_path = local" in source:
            nodes = ast.parse(source).body
            assignments = {n.targets[0].id: n for n in nodes if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
            start = assignments["venv"].lineno - 1
            end = assignments["requirements"].lineno - 1
            lines = source.splitlines(keepends=True)
            replacement = textwrap.dedent('''
                from research.routing.osrm_colab.venv_setup import create_environment
                from research.routing.osrm_colab.storage import tree_copy
                try:
                    creation = create_environment(local, selected)
                except BaseException:
                    # Persist captured stdout/stderr even when initialization fails.
                    try:
                        tree_copy(local / 'venv_diagnostics', pathlib.Path(CONFIG['drive_workspace']) / CONFIG['run_id'] / 'venv_diagnostics')
                    except Exception as persistence_error:
                        print('Drive copy failed; local diagnostics remain at', local / 'venv_diagnostics', persistence_error)
                    raise
                tree_copy(local / 'venv_diagnostics', pathlib.Path(CONFIG['drive_workspace']) / CONFIG['run_id'] / 'venv_diagnostics')
                python = creation['python']
                venv = pathlib.Path(python).parent.parent
                print('Validated isolated environment:', python, creation['method'])
            ''').lstrip()
            source = "".join(lines[:start]) + replacement + "".join(lines[end:])
        elif cell["cell_type"] == "markdown" and source.startswith("## 3."):
            source += "\nV4 captures ensurepip/venv stderr. It first tries standard venv and uses\na separately hash-locked virtualenv bootstrap ONLY for confirmed ensurepip\nunavailability. Bootstrap tools use a private target, not system Python.\nInvalid pre-existing environments are rejected. New failed attempts are moved\nto a quarantine directory, never accepted because bin/python happens to exist.\nDiagnostics are preserved locally and copied to Drive.\n"
        elif cell["cell_type"] == "markdown" and source.startswith("# DhakaNest"):
            source += "\n## Environment creation revision (v4)\nThe affected /usr/bin/python3 lacks ensurepip but has pip. V4 retains the\noriginal Python 3.12/3.13 research specifications and all 33 hashed research\ndependencies. Use the v4 ZIP and new run ID/local_root defaults. No prior\nnotebook, archive, benchmark or manifest is replaced.\n"
        cell["source"] = source.splitlines(keepends=True)
    return result


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v4.ipynb"
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(notebook(), output, indent=2)
        output.write("\n")
    print(path)
