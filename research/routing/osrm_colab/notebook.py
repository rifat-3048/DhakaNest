"""Generate a clean notebook artifact using JSON, without notebook dependencies."""

import json
from pathlib import Path
import textwrap


def notebook():
    cells = []
    def add(kind, text):
        cell = {"cell_type": kind, "id": f"phase3d-{len(cells):02d}", "metadata": {}, "source": textwrap.dedent(text).strip().splitlines(keepends=True)}
        # Keep each source line terminated so joining cells is unambiguous.
        cell["source"] = [line if line.endswith("\n") else line + "\n" for line in cell["source"]]
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)

    add("markdown", """
    # DhakaNest Phase 3D: native OSRM in Google Colab
    Select **Runtime > Change runtime type > CPU**. Run cells in order. No Docker,
    GPU, MongoDB, application server or public routing demo is used.

    First create the current byte-preserving input ZIP on your computer using
    the command in `research/routing/osrm_colab/README.md`. Upload it to Drive.
    This notebook alone does NOT contain the repository, model or benchmark.
    Enter its path and printed SHA-256 in the ONE configuration cell below.
    ZIP mode is recommended because historical evidence binds exact file bytes.
    An explicitly authorized HTTPS Git URL plus exact commit is an alternative,
    but it must contain all research files and model assets with matching bytes.

    Heavy stages can take hours. Free Colab RAM may be insufficient: resource
    guards stop rather than silently shrink Bangladesh or retry failed builds.
    A Drive mount is not a runtime guarantee. Read failures before enabling a
    retry. Keep the same run ID/configuration for resume, and use a new run ID
    if map, binary, library, profile, coordinates or acquisition settings change.
    Completion is established by actual matrix/fixture evidence, not this file.
    """)
    add("code", """
    CONFIG = {
        "run_id": "phase3d-colab-001",
        "drive_workspace": "/content/drive/MyDrive/DhakaNestResearch",
        "repository_zip": "/content/drive/MyDrive/DhakaNestResearch/dhakanest_colab_input_v2.zip",
        "repository_zip_sha256": "PASTE_THE_SHA256_PRINTED_BY_THE_BUNDLE_COMMAND",
        "git_url": "",
        "git_commit": "",
        "local_root": "/content/dhakanest_phase3d",
        "port": 5001,
        "threads": 1,
        "minimum_free_ram_gib": 6,
        "minimum_free_disk_gib": 20,
        "abort_below_ram_gib": 1,
        "maximum_download_gib": 2,
        "origin_batch": 40,
        "destination_batch": 12,
        "timeout_seconds": 60,
        "interval_seconds": 0.25,
        "retries": 2,
        "request_ceiling": 189,
        "allow_retry_failed_stage": False,
    }
    """)
    add("markdown", """
    ## 1. Mount persistent Drive
    Colab asks for your own account authorization. Never paste credentials here.
    """)
    add("code", """
    from google.colab import drive
    drive.mount('/content/drive')
    """)
    add("markdown", """
    ## 2. Import the current repository (local /content)
    The bootstrap loads only the stdlib storage helper from a ZIP whose complete
    SHA-256 you explicitly supplied. That helper verifies every member before
    extracting. Existing conflicting files cause a stop, never an overwrite.
    """)
    add("code", """
    import hashlib, json, pathlib, re, subprocess, sys, types, zipfile
    from urllib.parse import urlsplit
    local = pathlib.Path(CONFIG['local_root'])
    if not str(local).startswith('/content/') or '..' in local.parts or local.is_relative_to('/content/drive'):
        raise ValueError('Use a safe local /content compute directory')
    repo = local / 'repo'
    if CONFIG['git_url']:
        url = urlsplit(CONFIG['git_url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('Supply an explicitly authorized credential-free HTTPS repository URL')
        commit = CONFIG['git_commit']
        if not re.fullmatch(r'[a-fA-F0-9]{40}', commit):
            raise ValueError('An exact Git commit is required')
        if not repo.exists():
            subprocess.run(['git', 'clone', '--no-checkout', CONFIG['git_url'], str(repo)], check=True)
        subprocess.run(['git', '-C', str(repo), 'checkout', '--detach', commit], check=True)
        if subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() != commit:
            raise ValueError('Git revision mismatch')
    else:
        archive_path = pathlib.Path(CONFIG['repository_zip'])
        hasher = hashlib.sha256()
        with archive_path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                hasher.update(block)
        if hasher.hexdigest() != CONFIG['repository_zip_sha256']:
            raise ValueError('Input archive checksum mismatch; do not proceed')
        with zipfile.ZipFile(archive_path) as archive:
            helper = types.ModuleType('verified_colab_storage')
            source = archive.read('research/routing/osrm_colab/storage.py')
            exec(compile(source, 'verified_colab_storage.py', 'exec'), helper.__dict__)
            helper.extract_bundle(archive_path, repo, CONFIG['repository_zip_sha256'])
    sys.path.insert(0, str(repo))
    from research.routing.osrm_colab.workflow import validate_config, guard
    validate_config(CONFIG)
    print('Imported repository:', repo)
    print(json.dumps(guard(CONFIG), indent=2))
    """)
    add("markdown", """
    ## 3. Isolated Python environment and input verification
    Install pinned research dependencies into a dedicated venv, not the Colab
    kernel. Inputs are validated before any OSM download or native build.
    All production environment files were deliberately excluded from the ZIP.
    """)
    add("code", """
    from research.routing.osrm_colab.storage import put_json
    config_path = local / 'colab_config.json'
    # Only this local operational config may change to enable an explicit retry.
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(CONFIG, indent=2))
    venv = local / 'research_venv'
    if not (venv / 'bin/python').exists():
        subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
    python = str(venv / 'bin/python')
    requirements = repo / 'research/routing/osrm_colab/requirements-colab.txt'
    previous_inputs = pathlib.Path(CONFIG['drive_workspace']) / CONFIG['run_id'] / 'evidence/inputs.json'
    if previous_inputs.exists():
        # Reinstall the recorded full transitive environment on a new runtime.
        requirements = local / 'resumed-requirements.txt'
        requirements.write_text('\\n'.join(json.loads(previous_inputs.read_text())['python_dependencies']) + '\\n')
    subprocess.run([python, '-m', 'pip', 'install', '-r', str(requirements)], check=True)
    def stage(name):
        subprocess.run([python, '-u', '-m', 'research.routing.osrm_colab.workflow', name,
                        '--config', str(config_path)], cwd=repo, check=True)
    stage('inputs')
    """)
    add("markdown", """
    ## 4. Runtime resource readiness
    CPU, total/available RAM, disk, architecture, Python and tools are recorded.
    Conservative 6 GiB free RAM / 20 GiB free disk gates are not a promise that
    Bangladesh preprocessing fits every Colab runtime. One worker is default.
    """)
    add("code", "stage('runtime')")
    add("markdown", """
    ## 5. Pinned native OSRM build (no Docker)
    Official source release v5.27.1, exact commit recorded in the setup script.
    System packages and all binary/profile hashes are retained. On resume this
    restores OS libraries before checking saved binaries. Changed libraries
    require a new run rather than mixing snapshots. No unverified installer is
    downloaded. Review setup/preprocessing scripts in the repository.
    """)
    add("code", """
    subprocess.run(['bash', str(repo / 'research/routing/osrm_colab/install_dependencies.sh')], cwd=repo, check=True)
    stage('setup')
    """)
    add("markdown", """
    ## 6. Download and freeze Bangladesh OSM
    The actual PBF and provider polygon are hashed and persisted. OSM header
    metadata, download time, HTTP metadata, byte count and all benchmark bounds
    are recorded. A moving latest URL alone is never treated as a snapshot.
    No silently cropped substitute or straight-line fallback is permitted.
    """)
    add("code", "stage('download')")
    add("markdown", """
    ## 7. MLD preprocessing
    Extract -> partition -> customize; bounded workers and monitored free RAM.
    Completed graph files go to Drive. Failed/interrupted expensive stages stop
    until you review the logs and explicitly enable retry in the config cell.
    """)
    add("code", "stage('preprocess')")
    add("markdown", """
    ## 8. Local server, real smoke, bounded acquisition and finalization
    Starts an owned localhost-only server, preserves PID/logs and runs an actual
    first-batch smoke with duration/distance dimensions and snapping metadata.
    Then Phase 3C handles exact pairs, bounded retries and durable reservations.
    Successful captures are skipped on resume. No public OSRM demo is contacted.

    Only after all 30,000 logical pairs are genuine valid routes or verified
    double-null unreachable cells does the existing finalizer publish the new
    benchmark_v1_3_colab overlay, candidate counts/groups and independent blinded
    annotation pool. Missing/failed requests never become zero-duration routes.
    The server is stopped in a finally block, including on ordinary exceptions.
    A runtime termination may kill it before that block; rerun in a new runtime.
    """)
    add("code", "stage('acquire')")
    add("markdown", """
    ## 9. Offline verification (server now stopped)
    Uses stored profiles, properties, assessments, destinations and raw captures.
    No live OSRM, MongoDB, prediction generation or final ranking is needed.
    """)
    add("code", "stage('offline')")
    add("markdown", """
    ## 10. Regression tests and logs
    These tests are offline/mocked. They do not substitute for the genuine smoke
    and matrix evidence above. Preserve logs alongside the runtime reports.
    """)
    add("code", """
    from research.routing.osrm_colab.storage import copy_once, sha
    import time
    run_drive = pathlib.Path(CONFIG['drive_workspace']) / CONFIG['run_id']
    commands = [
        ([python, '-m', 'unittest', 'discover', '-s', 'research/tests'], repo, 'research-tests.log'),
        ([python, '-m', 'unittest', 'tests.test_recommendation_part1', 'tests.test_recommendation_part2',
          'tests.test_recommendation_part5', 'tests.test_recommendation_part7', 'tests.test_academic_inventory'],
         repo / 'backend', 'backend-tests.log'),
    ]
    proof_path = run_drive / 'regressions/accepted.json'
    dataset_manifest = repo / 'research/datasets/benchmark_v1_3_colab/dataset_manifest.json'
    if proof_path.exists():
        proof = json.loads(proof_path.read_text())
        if proof['dataset_manifest_sha256'] != sha(dataset_manifest):
            raise ValueError('Regression evidence belongs to a different dataset')
        for relative, expected in proof['log_hashes'].items():
            if sha(run_drive / relative) != expected:
                raise ValueError('Saved regression log changed')
        print('Reused verified passing regression evidence:', proof_path)
    else:
        attempt = str(time.time_ns())
        proof = {'dataset_manifest_sha256': sha(dataset_manifest), 'log_hashes': {}, 'tests': {},
                 'all_passed': True, 'phase4_authorized': False}
        for command, directory, name in commands:
            result = subprocess.run(command, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            print(result.stdout)
            logfile = local / name
            logfile.write_text(result.stdout)
            relative = 'regressions/' + attempt + '/' + name
            proof['log_hashes'][relative] = copy_once(logfile, run_drive / relative)
            count = re.search(r'Ran (\\d+) tests', result.stdout)
            if result.returncode or not count or not re.search(r'\\nOK\\s*$', result.stdout):
                raise RuntimeError('Regression failure/skips; do not claim Phase 3D complete')
            proof['tests'][name] = int(count.group(1))
        subprocess.run([python, '-m', 'compileall', '-q', 'research/routing/osrm_colab'], cwd=repo, check=True)
        put_json(proof_path, proof)
    put_json(repo / 'research/results/phase_3d_colab' / CONFIG['run_id'] / 'colab_acceptance.json', proof)
    copy_once(repo / 'research/results/phase_3d_colab' / CONFIG['run_id'] / 'colab_acceptance.json',
              run_drive / 'results/colab_acceptance.json')
    print('Routing-backed offline verification and regression checks passed:', proof['tests'])
    """)
    add("markdown", """
    ## 11. Export and interpretation
    Drive contains immutable checkpoints, original map, compiled graph/binaries,
    final dataset, reports, and a self-contained offline ZIP including raw captures.
    Keep the map/graph in Drive, not Git. See OpenStreetMap ODbL attribution.
    Hash-verify the ZIP before extraction using the supplied storage helper.
    Later fixtures must preserve the research-relative raw capture paths.

    Listings/coordinates remain synthetic; destinations are area anchors; OSRM
    driving durations are not observed Dhaka traffic. Model fairness is not
    independent market truth. Human annotation requires a separate pilot/ethics
    review and explicit Phase 4 approval. No labels or evaluation metrics ran.
    """)
    add("code", """
    export = run_drive / (CONFIG['run_id'] + '-offline.zip')
    print('Offline export:', export)
    print('SHA-256:', hashlib.file_digest(export.open('rb'), 'sha256').hexdigest())
    print('Reports:', run_drive / 'results')
    print('Regressions:', run_drive / 'regressions')
    print('Post-export acceptance proof:', run_drive / 'results/colab_acceptance.json')
    print('Review actual counts and logs. Notebook creation alone is NOT Phase 3D completion.')
    """)
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"}, "colab": {"name": "DhakaNest_Phase3D_Colab_OSRM.ipynb"}},
            "nbformat": 4, "nbformat_minor": 5}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Regenerate this new notebook before sealing/releasing it")
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[2] / "notebooks/DhakaNest_Phase3D_Colab_OSRM.ipynb"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w" if args.refresh else "x", encoding="utf-8", newline="\n") as stream:
        json.dump(notebook(), stream, indent=2)
        stream.write("\n")
    print(output)


if __name__ == "__main__":
    main()
