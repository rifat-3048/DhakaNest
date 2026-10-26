"""Test failures that would invalidate the Phase 2 evidence package."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from research.literature.validate_literature import (
    LiteratureValidationError, bibtex_keys, normalize_doi,
    validate_records, validate_workspace,
)


ROOT = Path(__file__).resolve().parents[1]


class LiteratureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.papers = json.loads((ROOT / 'literature/paper_registry.json').read_text(encoding='utf-8'))['papers']
        cls.hypotheses = {item['id'] for item in json.loads((ROOT / 'protocols/hypotheses.json').read_text())['hypotheses']}
        cls.questions = {item['id'] for item in json.loads((ROOT / 'protocols/research_questions.json').read_text())['research_questions']}
        cls.comparisons = set()
        for filename, key in [('baseline_specifications.json', 'baselines'), ('ablation_specifications.json', 'ablations')]:
            cls.comparisons.update(item['id'] for item in json.loads((ROOT / 'protocols' / filename).read_text())[key])

    def validate(self, papers):
        return validate_records(papers, self.hypotheses, self.questions, self.comparisons)

    def test_workspace_views_and_references_agree(self):
        summary = validate_workspace()
        self.assertEqual(summary['retained'], 31)
        self.assertEqual(summary['deeply_analyzed_full_text'], 26)
        self.assertEqual(summary['screened_records'], 40)

    def test_case_and_url_variant_doi_duplicates_fail(self):
        papers = deepcopy(self.papers)
        papers[1]['doi'] = 'https://doi.org/' + papers[0]['doi'].upper()
        with self.assertRaisesRegex(LiteratureValidationError, 'Duplicate DOI'):
            self.validate(papers)

    def test_duplicate_study_versions_fail(self):
        papers = deepcopy(self.papers)
        papers[1]['study_id'] = papers[0]['study_id']
        with self.assertRaisesRegex(LiteratureValidationError, 'publication version'):
            self.validate(papers)

    def test_relabeling_a_duplicate_publication_does_not_count_twice(self):
        papers = deepcopy(self.papers)
        papers[1]['title'] = papers[0]['title'].upper()
        with self.assertRaisesRegex(LiteratureValidationError, 'Duplicate publication title'):
            self.validate(papers)

    def test_metadata_cannot_pad_full_text_count(self):
        papers = deepcopy(self.papers)
        for paper in papers:
            paper['evidence_access'] = 'metadata_only'
        with self.assertRaisesRegex(LiteratureValidationError, '25 required'):
            self.validate(papers)

    def test_missing_analysis_fails(self):
        papers = deepcopy(self.papers)
        papers[0]['critical_analysis'] = 'Good method.'
        with self.assertRaisesRegex(LiteratureValidationError, 'Substantive analysis'):
            self.validate(papers)

    def test_unknown_hypothesis_fails(self):
        papers = deepcopy(self.papers)
        papers[0]['hypothesis_ids'] = ['H999']
        with self.assertRaisesRegex(LiteratureValidationError, 'hypothesis reference'):
            self.validate(papers)

    def test_preprint_peer_review_claim_fails(self):
        papers = deepcopy(self.papers)
        next(p for p in papers if p['publication_type'] == 'preprint')['peer_review_status'] = 'journal_publication_verified'
        with self.assertRaisesRegex(LiteratureValidationError, 'falsely labeled'):
            self.validate(papers)

    def test_broken_bibtex_fails(self):
        with self.assertRaises(LiteratureValidationError):
            bibtex_keys('@article{P01, title = {Unclosed title')

    def test_doi_normalization(self):
        self.assertEqual(normalize_doi('https://doi.org/10.1234/ABCD'), '10.1234/abcd')


if __name__ == '__main__':
    unittest.main()
