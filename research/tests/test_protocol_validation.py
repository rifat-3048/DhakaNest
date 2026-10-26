"""Cross-file consistency tests for the Phase 1 research protocols."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from research.protocols.validate_protocols import (
    ProtocolValidationError,
    load_protocols,
    validate_protocols,
)


RESEARCH_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_DIRECTORY = RESEARCH_ROOT / "protocols"


class ProtocolValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocols = load_protocols(PROTOCOL_DIRECTORY)

    def validate(self, protocols=None):
        return validate_protocols(
            self.protocols if protocols is None else protocols,
            research_root=RESEARCH_ROOT,
        )

    def test_committed_protocols_are_consistent(self) -> None:
        summary = self.validate()
        self.assertEqual(summary["protocol_files"], 8)
        self.assertEqual(summary["research_questions"], 6)
        self.assertEqual(summary["hypotheses"], 8)
        self.assertEqual(summary["baselines"], 8)
        self.assertEqual(summary["ablations"], 9)

    def test_duplicate_identifier_is_rejected(self) -> None:
        protocols = deepcopy(self.protocols)
        questions = protocols["research_questions.json"]["research_questions"]
        questions[1]["id"] = questions[0]["id"]
        with self.assertRaisesRegex(ProtocolValidationError, "duplicate IDs"):
            self.validate(protocols)

    def test_unknown_hypothesis_question_is_rejected(self) -> None:
        protocols = deepcopy(self.protocols)
        protocols["hypotheses.json"]["hypotheses"][0]["rq_id"] = "RQ999"
        with self.assertRaisesRegex(ProtocolValidationError, "unknown RQ999"):
            self.validate(protocols)

    def test_primary_question_requires_primary_hypothesis(self) -> None:
        protocols = deepcopy(self.protocols)
        for hypothesis in protocols["hypotheses.json"]["hypotheses"]:
            if hypothesis["rq_id"] == "RQ1":
                hypothesis["classification"] = "supporting"
        with self.assertRaisesRegex(ProtocolValidationError, "without primary"):
            self.validate(protocols)

    def test_unknown_ablation_control_is_rejected(self) -> None:
        protocols = deepcopy(self.protocols)
        protocols["ablation_specifications.json"]["ablations"][0][
            "comparison_control"
        ] = "B_UNKNOWN"
        with self.assertRaisesRegex(ProtocolValidationError, "unknown comparison"):
            self.validate(protocols)

    def test_invalid_metric_convention_is_rejected(self) -> None:
        protocols = deepcopy(self.protocols)
        metrics = protocols["evaluation_protocol.json"]["metrics"]
        next(item for item in metrics if item["id"] == "Precision@5")[
            "definition"
        ] = "Relevant count divided by returned count."
        with self.assertRaisesRegex(ProtocolValidationError, "fixed-K"):
            self.validate(protocols)

    def test_output_path_cannot_escape_research(self) -> None:
        protocols = deepcopy(self.protocols)
        protocols["annotation_protocol.json"]["output_paths"] = ["../outside"]
        with self.assertRaisesRegex(ProtocolValidationError, "outside research"):
            self.validate(protocols)


if __name__ == "__main__":
    unittest.main()
