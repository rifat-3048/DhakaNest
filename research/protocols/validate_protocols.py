"""Validate the cross-file Phase 1 research protocol contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROTOCOL_FILES = (
    "research_questions.json",
    "hypotheses.json",
    "baseline_specifications.json",
    "ablation_specifications.json",
    "evaluation_protocol.json",
    "benchmark_requirements.json",
    "annotation_protocol.json",
    "statistical_analysis_plan.json",
)


class ProtocolValidationError(ValueError):
    """Raised when protocol files are incomplete or inconsistent."""


def _require_text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolValidationError(f"{location} must be a non-empty string.")
    return value.strip()


def _require_fields(item: dict[str, Any], fields: set[str], location: str) -> None:
    missing = sorted(fields - set(item))
    if missing:
        raise ProtocolValidationError(f"{location} is missing fields: {missing}")


def _ids(items: list[dict[str, Any]], location: str) -> set[str]:
    values = [_require_text(item.get("id"), f"{location}.id") for item in items]
    if len(values) != len(set(values)):
        raise ProtocolValidationError(f"{location} contains duplicate IDs.")
    return set(values)


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def load_protocols(protocol_directory: Path) -> dict[str, dict[str, Any]]:
    """Load only the eight declared protocol files."""
    protocols: dict[str, dict[str, Any]] = {}
    for filename in PROTOCOL_FILES:
        path = protocol_directory / filename
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProtocolValidationError(f"Cannot load {filename}: {error}") from error
        if not isinstance(value, dict):
            raise ProtocolValidationError(f"{filename} must contain a JSON object.")
        protocols[filename] = value
    return protocols


def validate_protocols(
    protocols: dict[str, dict[str, Any]], *, research_root: Path
) -> dict[str, int]:
    """Validate identifiers, references, metric rules, and safe output paths."""
    missing_files = sorted(set(PROTOCOL_FILES) - set(protocols))
    if missing_files:
        raise ProtocolValidationError(f"Missing protocol files: {missing_files}")

    for filename in PROTOCOL_FILES:
        protocol = protocols[filename]
        _require_text(protocol.get("protocol_version"), f"{filename}.protocol_version")
        _require_text(protocol.get("protocol_id"), f"{filename}.protocol_id")
        outputs = protocol.get("output_paths")
        if not isinstance(outputs, list) or not outputs:
            raise ProtocolValidationError(f"{filename}.output_paths must be non-empty.")
        for value in outputs:
            relative = _require_text(value, f"{filename}.output_paths item")
            if Path(relative).is_absolute() or not _is_inside(
                research_root / relative, research_root
            ):
                raise ProtocolValidationError(
                    f"{filename} contains an output path outside research/."
                )

    questions = protocols["research_questions.json"].get("research_questions")
    hypotheses = protocols["hypotheses.json"].get("hypotheses")
    baselines = protocols["baseline_specifications.json"].get("baselines")
    ablations = protocols["ablation_specifications.json"].get("ablations")
    metrics = protocols["evaluation_protocol.json"].get("metrics")
    for name, items in (
        ("research_questions", questions),
        ("hypotheses", hypotheses),
        ("baselines", baselines),
        ("ablations", ablations),
        ("metrics", metrics),
    ):
        if not isinstance(items, list) or not items:
            raise ProtocolValidationError(f"{name} must be a non-empty list.")

    question_ids = _ids(questions, "research_questions")
    hypothesis_ids = _ids(hypotheses, "hypotheses")
    baseline_ids = _ids(baselines, "baselines")
    ablation_ids = _ids(ablations, "ablations")
    metric_ids = _ids(metrics, "metrics")

    question_fields = {
        "id", "classification", "objective", "independent_variables",
        "dependent_variables", "required_datasets", "comparison_methods",
        "primary_metrics", "supporting_metrics", "statistical_analysis",
        "confounding_factors", "answerability",
    }
    for question in questions:
        _require_fields(question, question_fields, f"question {question.get('id')}")
        if question["classification"] not in {"primary", "supporting"}:
            raise ProtocolValidationError("Question classification is invalid.")
        if not question["primary_metrics"]:
            raise ProtocolValidationError(
                f"Question {question['id']} has no primary metric."
            )
        for reference in question["comparison_methods"]:
            if reference.startswith("B_") and reference not in baseline_ids:
                raise ProtocolValidationError(
                    f"Question {question['id']} references unknown baseline {reference}."
                )
            if reference.startswith("A_") and reference not in ablation_ids:
                raise ProtocolValidationError(
                    f"Question {question['id']} references unknown ablation {reference}."
                )

    hypothesis_fields = {
        "id", "rq_id", "null_hypothesis", "alternative_hypothesis",
        "compared_conditions", "primary_outcome", "unit_of_analysis",
        "required_evidence", "statistical_test", "interpretation",
    }
    primary_hypothesis_questions: set[str] = set()
    for hypothesis in hypotheses:
        _require_fields(
            hypothesis, hypothesis_fields, f"hypothesis {hypothesis.get('id')}"
        )
        if hypothesis["rq_id"] not in question_ids:
            raise ProtocolValidationError(
                f"Hypothesis {hypothesis['id']} references unknown {hypothesis['rq_id']}."
            )
        if hypothesis.get("classification") == "primary":
            primary_hypothesis_questions.add(hypothesis["rq_id"])
        for reference in hypothesis["compared_conditions"]:
            if reference.startswith("B_") and reference not in baseline_ids:
                raise ProtocolValidationError(
                    f"Hypothesis {hypothesis['id']} references unknown {reference}."
                )
            if reference.startswith("A_") and reference not in ablation_ids:
                raise ProtocolValidationError(
                    f"Hypothesis {hypothesis['id']} references unknown {reference}."
                )

    primary_questions = {
        item["id"] for item in questions if item["classification"] == "primary"
    }
    uncovered = sorted(primary_questions - primary_hypothesis_questions)
    if uncovered:
        raise ProtocolValidationError(
            f"Primary questions without primary hypotheses: {uncovered}"
        )

    baseline_fields = {
        "id", "name", "kind", "safety_eligibility", "candidate_selection",
        "ordering", "top_k_policy", "purpose",
    }
    for baseline in baselines:
        _require_fields(
            baseline, baseline_fields, f"baseline {baseline.get('id')}"
        )
        if baseline["safety_eligibility"] is not True:
            raise ProtocolValidationError(
                f"Baseline {baseline['id']} must preserve safety eligibility."
            )

    ablation_fields = {
        "id", "component_removed", "comparison_control",
        "architectural_effect", "weight_policy", "evaluation_metrics",
        "interpretation", "confounders",
    }
    for ablation in ablations:
        _require_fields(
            ablation, ablation_fields, f"ablation {ablation.get('id')}"
        )
        if ablation["comparison_control"] not in baseline_ids:
            raise ProtocolValidationError(
                f"Ablation {ablation['id']} has unknown comparison control."
            )
        if not ablation["evaluation_metrics"]:
            raise ProtocolValidationError(
                f"Ablation {ablation['id']} has no evaluation metrics."
            )

    evaluation = protocols["evaluation_protocol.json"]
    relevance = evaluation.get("relevance", {})
    if relevance.get("scale") != [0, 1, 2, 3]:
        raise ProtocolValidationError("Relevance scale must be [0, 1, 2, 3].")
    if relevance.get("binary_relevance_threshold") != 2:
        raise ProtocolValidationError("Binary relevance threshold must be 2.")
    if not {"NDCG@5", "NDCG@10"}.issubset(metric_ids):
        raise ProtocolValidationError("NDCG@5 and NDCG@10 are required metrics.")
    primary_metric_ids = {
        item["id"] for item in metrics if item.get("role") == "primary"
    }
    if primary_metric_ids != {"NDCG@5", "NDCG@10"}:
        raise ProtocolValidationError(
            "Exactly NDCG@5 and NDCG@10 must be primary evaluation metrics."
        )
    for metric in metrics:
        if metric["id"].startswith("Precision@") and "fixed K" not in metric.get(
            "definition", ""
        ):
            raise ProtocolValidationError(
                f"{metric['id']} must use a fixed-K denominator."
            )

    return {
        "protocol_files": len(PROTOCOL_FILES),
        "research_questions": len(question_ids),
        "hypotheses": len(hypothesis_ids),
        "baselines": len(baseline_ids),
        "ablations": len(ablation_ids),
        "metrics": len(metric_ids),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol-dir", type=Path, default=Path(__file__).resolve().parent
    )
    args = parser.parse_args()
    protocol_directory = args.protocol_dir.resolve()
    research_root = protocol_directory.parent
    summary = validate_protocols(
        load_protocols(protocol_directory), research_root=research_root
    )
    print(json.dumps({"status": "ok", **summary}, indent=2))


if __name__ == "__main__":
    main()
