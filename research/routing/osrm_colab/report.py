"""Write new Colab evidence, without revising any historical phase report."""

import json
from pathlib import Path

from .storage import put_json, sha

LIMITATIONS = """The 2,500 active listings are synthetic academic records; property coordinates
are generated around area anchors. Destinations are area anchors, not verified
institution addresses. OSRM routes use a frozen OSM road network and car profile,
not observed Dhaka traffic. Snapping may move synthetic coordinates to roads.
Frozen XGBoost assessments are model outputs, not independent market truth.
These controlled synthetic data cannot establish real-market generalization.
Colab does not remove these limitations. No human labels, final ranking metrics,
baseline comparisons or ablation experiments are produced in this phase.
"""


def write_reports(directory, reports, record):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in reports.items():
        path = directory / name
        text = f"# {name.removesuffix('.md').replace('_', ' ').title()}\n\n{body.strip()}\n"
        if path.exists():
            if path.read_text(encoding="utf-8") != text:
                raise ValueError(f"Report would overwrite different evidence: {path}")
        else:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
    put_json(directory / "verification_results.json", record)
    files = {p.name: sha(p) for p in sorted(directory.iterdir()) if p.is_file() and p.name != "phase_3d_colab_manifest.json"}
    put_json(directory / "phase_3d_colab_manifest.json", {"status": record["status"], "files": files,
             "production_modified": False, "phase4_authorized": False})


def runtime_reports(workflow, verified):
    read = lambda p: json.loads(Path(p).read_text())
    coverage = read(workflow.output / "candidate_coverage.json")
    annotation = read(workflow.output / "annotation_status.json")
    acquisitions = sorted(workflow.evidence.glob("acquisition-*.json"))
    summary = read(acquisitions[-1])
    put_json(workflow.output / "benchmark_readiness.json", {"routing_complete": True,
        "offline_fixture_verified": True, "annotation_routing_material_ready": annotation["routing_ready"],
        "annotation_pilot_complete": False, "phase4_authorized": False,
        "ranking_metrics_ready": False, "reason": "No independent judgments; separate pilot/ethics and Phase 4 approval needed"})
    # The original dataset manifest remains immutable. This small sidecar binds
    # the later readiness evidence rather than mutating the sealed file inventory.
    put_json(workflow.output / "colab_provenance_manifest.json", {
        "dataset_manifest_sha256": sha(workflow.output / "dataset_manifest.json"),
        "readiness_sha256": sha(workflow.output / "benchmark_readiness.json"),
        "evidence_files": {p.relative_to(workflow.evidence).as_posix(): sha(p)
                           for p in sorted(workflow.evidence.rglob("*")) if p.is_file()},
        "configuration_sha256": sha(workflow.drive / "configuration.json")})
    record = {"status": "routing_benchmark_finalized_pending_human_pilot", **verified,
              "scope_sha256": read(workflow.output / "routing/request_plan.json")["scope_sha256"],
              "acquisition": summary, "smoke_requests": len(list(workflow.evidence.glob("smoke_requests/*.started.json"))),
              "phase4_ready": False}
    reports = {
        "runtime_readiness.md": "Actual Colab runtime inspections:\n\n" + "\n".join(
            json.dumps(read(p), sort_keys=True) for p in sorted(workflow.evidence.glob("runtime-*.json"))),
        "osm_dataset_provenance.md": json.dumps(read(workflow.evidence / "download.json"), indent=2),
        "osrm_setup.md": json.dumps({"setup": read(workflow.evidence / "setup.json"),
                                     "preprocess": read(workflow.evidence / "preprocess.json")}, indent=2),
        "routing_acquisition.md": json.dumps(summary, indent=2) + "\nSmoke calls are additional to batch attempt reservations.",
        "frozen_matrix_validation.md": json.dumps(verified["routing"], indent=2),
        "commute_candidate_coverage.md": json.dumps(coverage, indent=2) + "\nPer-profile stage counts: verification_results.json.",
        "annotation_pool_finalization.md": json.dumps(annotation, indent=2) +
            "\nIndependent seeded sampling reused; future nominations can use research.benchmark.build_annotation_pool.merge_nominations. No labels collected.",
        "offline_fixture_verification.md": json.dumps({k: v for k, v in verified.items() if k != "per_profile_counts"}, indent=2),
        "research_limitations.md": LIMITATIONS,
        "phase_3d_colab_verification.md": "Routing-backed fixture and matrix checks passed. Historical hashes preserved. "
            "Run the notebook regression cell and retain its actual test logs before claiming full Phase 3D acceptance. "
            "Source/test validation on Windows is recorded separately; no inference, ranking experiment, DB access or production change occurred.",
    }
    write_reports(workflow.results, reports, record)


def local_reports(record, directory):
    missing = "NOT EXECUTED in Colab. No runtime, OSM download, preprocessing, smoke or routing evidence was generated on Windows."
    reports = {name: missing for name in (
        "runtime_readiness.md", "osm_dataset_provenance.md", "osrm_setup.md", "routing_acquisition.md",
        "frozen_matrix_validation.md", "commute_candidate_coverage.md", "annotation_pool_finalization.md",
        "offline_fixture_verification.md")}
    reports.update({"research_limitations.md": LIMITATIONS,
        "phase_3d_colab_verification.md": "PARTIALLY COMPLETE: executable workflow implemented and locally validated.\n\n" +
        json.dumps(record, indent=2) + "\n\nHistorical route evidence remains 0 valid, 0 unreachable, 30,000 missing. "
        "Final candidate distribution and pool size remain unknown. Phase 4 is not ready or authorized."})
    write_reports(directory, reports, record)
