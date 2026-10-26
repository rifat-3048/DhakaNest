"""Create the v3 compatibility notebook without overwriting the v2 notebook."""

import ast
import json
from pathlib import Path
import pprint
import textwrap

from .notebook import notebook as original_notebook


def notebook():
    result = original_notebook()
    result["metadata"]["colab"]["name"] = "DhakaNest_Phase3D_Colab_OSRM_v3.ipynb"
    result["metadata"]["language_info"].pop("version", None)
    for cell in result["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.startswith("CONFIG ="):
            config = ast.literal_eval(ast.parse(source).body[0].value)
            config.update(run_id="phase3d-colab-pycompat-001", local_root="/content/dhakanest_phase3d_pycompat",
                          repository_zip="/content/drive/MyDrive/DhakaNestResearch/dhakanest_colab_input_v3.zip")
            source = "CONFIG = " + pprint.pformat(config, sort_dicts=False) + "\n"
        elif cell["cell_type"] == "code" and "config_path = local" in source:
            source = textwrap.dedent('''
                from research.routing.osrm_colab.storage import put_json
                from research.routing.osrm_colab.environment import select_environment, check_resume
                selected = select_environment()
                print('Kernel:', sys.version, 'Architecture:', __import__('platform').machine())
                print('Research environment:', selected['id'])
                CONFIG['research_environment_id'] = selected['id']
                CONFIG['research_environment_spec_sha256'] = selected['specification_sha256']
                config_path = local / 'colab_config.json'
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(json.dumps(CONFIG, indent=2))
                # Never reuse a venv created by another Python minor version.
                venv = local / ('research_venv_cp' + selected['python_minor'].replace('.', ''))
                if not (venv / 'bin/python').exists():
                    subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
                python = str(venv / 'bin/python')
                actual_minor = subprocess.check_output([python, '-c', 'import sys; print(str(sys.version_info.major)+"."+str(sys.version_info.minor))'], text=True).strip()
                if actual_minor != selected['python_minor']:
                    raise ValueError('Existing virtual environment belongs to a different Python; use a new local_root')
                requirements = pathlib.Path(selected['installation_path'])
                previous_inputs = pathlib.Path(CONFIG['drive_workspace']) / CONFIG['run_id'] / 'evidence/inputs.json'
                if previous_inputs.exists():
                    previous = json.loads(previous_inputs.read_text())
                    check_resume(previous, selected)
                    if 'installation_lock' not in selected:
                        requirements = local / 'resumed-requirements.txt'
                        requirements.write_text('\\n'.join(previous['python_dependencies']) + '\\n')
                install = [python, '-m', 'pip', 'install', '--only-binary=:all:']
                if 'installation_lock' in selected:
                    install.append('--require-hashes')
                # Save the actual wheel provenance selected inside Colab.
                report_path = local / 'python-install-report.json'
                install += ['--report', str(report_path), '-r', str(requirements)]
                subprocess.run(install, cwd=repo, check=True)
                subprocess.run([python, '-m', 'pip', 'check'], check=True)
                subprocess.run([python, '-m', 'research.routing.osrm_colab.environment', '--verify-installed'], cwd=repo, check=True)
                def stage(name):
                    subprocess.run([python, '-u', '-m', 'research.routing.osrm_colab.workflow', name,
                                    '--config', str(config_path)], cwd=repo, check=True)
                stage('inputs')
                from research.routing.osrm_colab.storage import copy_once
                import time
                provenance = pathlib.Path(CONFIG['drive_workspace']) / CONFIG['run_id'] / 'python_installations'
                copy_once(report_path, provenance / (str(time.time_ns()) + '.json'))
            ''').strip() + '\n'
        elif cell["cell_type"] == "markdown" and source.startswith("## 3."):
            source += "\nCPython 3.12 retains the original pins. CPython 3.13 selects a separately\nversioned environment (NumPy 2.1.3 / pandas 2.2.3) and a complete hashed\nLinux wheel lock. Python 3.11 and 3.14 remain unsupported. Exact versions,\nimports, pip check and full Colab regressions must pass. No model inference\nor training is used to establish package compatibility. Use a new run ID and\nlocal_root; old captures/environments must not be merged.\n"
        elif cell["cell_type"] == "markdown" and source.startswith("# DhakaNest"):
            source += "\n## Python compatibility revision\nThis v3 notebook supports stable CPython 3.12.x and 3.13.x on Linux x86_64.\nThe original notebook, environment pins and previous ZIP remain unchanged.\nThe reported affected kernel was CPython 3.13.16. Wheel availability and\ndependency closure are validated; actual Colab imports/regressions are still\nmandatory. No Phase 3D completion is claimed by this compatibility revision.\n"
        cell["source"] = source.splitlines(keepends=True)
    return result


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v3.ipynb"
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(notebook(), output, indent=2)
        output.write("\n")
    print(path)
