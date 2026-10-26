"""Validate curated literature identity, access, references and derived views.

Offline validation checks consistency; it does not authenticate a DOI online or
certify scientific claims. Source examination remains a documented human task.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from research.literature.export_literature import build_exports, MATRIX_FIELDS


ROOT = Path(__file__).resolve().parents[1]
ACCESS = {"full_text_examined", "abstract_and_metadata_examined", "metadata_only"}
CATEGORIES = set("ABCDEF")
REQUIRED = set(MATRIX_FIELDS) - {"full_citation"} | {
    "title", "authors", "venue", "study_id", "publication_type", "critical_analysis", "metadata_url",
}


class LiteratureValidationError(ValueError):
    """An evidence identity or consistency requirement failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LiteratureValidationError(message)


def normalize_doi(value: str) -> str:
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I).lower()


def bibtex_keys(text: str) -> list[str]:
    """Check the restricted brace-delimited BibTeX format emitted by exporter."""
    keys = []
    position = 0
    while position < len(text):
        if text[position].isspace():
            position += 1
            continue
        match = re.match(r"@(article|inproceedings|misc)\{(P\d{2}),\s*", text[position:])
        _require(match is not None, "Malformed BibTeX entry header.")
        keys.append(match.group(2))
        position += match.end()
        fields = set()
        while True:
            while position < len(text) and text[position].isspace():
                position += 1
            _require(position < len(text), "Unclosed BibTeX entry.")
            if text[position] == "}":
                position += 1
                break
            field = re.match(r"([a-z]+)\s*=\s*\{", text[position:])
            _require(field is not None, "Malformed BibTeX field.")
            _require(field.group(1) not in fields, "Duplicate BibTeX field.")
            fields.add(field.group(1))
            position += field.end()
            depth = 1
            while position < len(text) and depth:
                char = text[position]
                if char == "\\":
                    position += 2
                    continue
                depth += (char == "{") - (char == "}")
                position += 1
            _require(depth == 0, "Unbalanced BibTeX value braces.")
            while position < len(text) and text[position].isspace():
                position += 1
            if position < len(text) and text[position] == ",":
                position += 1
        _require({"title", "author", "year", "url"} <= fields, "Missing BibTeX citation fields.")
    _require(len(keys) == len(set(keys)), "Duplicate BibTeX keys.")
    return keys


def validate_records(papers: list[dict], hypothesis_ids: set[str], question_ids: set[str], comparison_ids: set[str]) -> dict:
    _require(len(papers) >= 30, "Target of 30 retained publications not met.")
    identifiers, studies, dois, titles = set(), set(), set(), set()
    full = 0
    for paper in papers:
        _require(REQUIRED <= paper.keys(), f"Missing fields for {paper.get('id')}.")
        paper_id = paper["id"]
        _require(re.fullmatch(r"P\d{2}", paper_id) is not None, "Invalid paper ID.")
        _require(paper_id not in identifiers, "Duplicate paper ID.")
        _require(paper["study_id"] not in studies, "Duplicate publication version/study.")
        identifiers.add(paper_id)
        studies.add(paper["study_id"])
        canonical_title = re.sub(r"[^a-z0-9]", "", paper["title"].lower())
        _require(canonical_title not in titles, "Duplicate publication title/version.")
        titles.add(canonical_title)
        _require(paper["evidence_access"] in ACCESS, "Unsupported evidence access.")
        _require(bool(paper["categories"]) and set(paper["categories"]) <= CATEGORIES, "Invalid categories.")
        _require(isinstance(paper["year"], int) and 1900 <= paper["year"] <= 2026, "Invalid publication year.")
        _require(isinstance(paper["authors"], list) and all(paper["authors"]), "Missing authors.")
        for field in ("title", "venue", "source_location", "critical_analysis", "verification_status"):
            _require(isinstance(paper[field], str) and paper[field].strip(), f"Missing {field}.")
        for field in ("url", "metadata_url"):
            parsed = urlparse(paper[field])
            _require(parsed.scheme in {"https", "http"} and bool(parsed.netloc), f"Invalid {field}.")
            _require(not parsed.username and not parsed.password, "Credentials in source URL.")
        if paper["doi"] is not None:
            doi = normalize_doi(paper["doi"])
            _require(re.fullmatch(r"10\.\d{4,9}/\S+", doi) is not None, "Invalid DOI syntax.")
            _require(doi not in dois, "Duplicate DOI.")
            dois.add(doi)
        _require(set(paper["hypothesis_ids"]) <= hypothesis_ids, "Unknown hypothesis reference.")
        _require(set(paper["rq_ids"]) <= question_ids, "Unknown question reference.")
        _require(set(paper["comparison_ids"]) <= comparison_ids, "Unknown baseline/ablation reference.")
        if paper["publication_type"] == "preprint":
            _require(paper["peer_review_status"] == "unverified_preprint", "Preprint falsely labeled peer reviewed.")
        if paper["evidence_access"] == "full_text_examined":
            _require(len(paper["critical_analysis"].split()) >= 60, f"Substantive analysis missing for {paper_id}.")
            _require("Not accessible" not in paper["source_location"], "Untraceable full-text analysis.")
            full += 1
    _require(full >= 25, f"Only {full} substantive full-text reviews; 25 required.")
    _require(set().union(*(set(p['categories']) for p in papers)) == CATEGORIES, "Missing theme coverage.")
    _require(set().union(*(set(p['hypothesis_ids']) for p in papers)) == hypothesis_ids, "Hypothesis coverage incomplete.")
    return {"retained": len(papers), "deeply_analyzed_full_text": full,
            "access": dict(Counter(p["evidence_access"] for p in papers)),
            "doi_entries_checked_for_format_and_duplicates": len(dois), "categories": sorted(CATEGORIES)}


def validate_workspace(root: Path = ROOT) -> dict:
    literature = root / "literature"
    papers = json.loads((literature / "paper_registry.json").read_text(encoding="utf-8"))["papers"]
    hypotheses = json.loads((root / "protocols" / "hypotheses.json").read_text(encoding="utf-8"))["hypotheses"]
    questions = json.loads((root / "protocols" / "research_questions.json").read_text(encoding="utf-8"))["research_questions"]
    baseline = json.loads((root / "protocols" / "baseline_specifications.json").read_text(encoding="utf-8"))["baselines"]
    ablation = json.loads((root / "protocols" / "ablation_specifications.json").read_text(encoding="utf-8"))["ablations"]
    summary = validate_records(papers, {h['id'] for h in hypotheses}, {q['id'] for q in questions}, {x['id'] for x in baseline + ablation})
    additions = json.loads((literature / "screening_additions.json").read_text(encoding="utf-8"))["records"]
    for path, expected in build_exports(papers, additions).items():
        # build_exports uses the module workspace; translate for explicit test roots.
        target = root / path.relative_to(ROOT)
        _require(target.read_text(encoding="utf-8") == expected, f"Stale or inconsistent export: {target.name}")
    keys = bibtex_keys((literature / "references.bib").read_text(encoding="utf-8"))
    _require(set(keys) == {p["id"] for p in papers}, "Bibliography/registry mismatch.")
    manuscript = (root / "results/phase_2/related_work_manuscript.md").read_text(encoding="utf-8")
    cited_ids = {f"P{int(number):02d}" for number in re.findall(r"\[(\d+)\]\(", manuscript)}
    _require(cited_ids <= {p["id"] for p in papers}, "Unknown manuscript citation.")
    rows = list(csv.DictReader(io.StringIO((literature / "screening_log.csv").read_text(encoding="utf-8"))))
    _require(len({r['id'] for r in rows}) == len(rows), "Duplicate screening record.")
    summary["screened_records"] = len(rows)
    summary["screening_decisions"] = dict(Counter(r["decision"] for r in rows))
    return summary


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps({"status": "ok", **validate_workspace()}, indent=2))


if __name__ == "__main__":
    main()
