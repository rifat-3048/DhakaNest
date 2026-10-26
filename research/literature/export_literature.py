"""Build consistent CSV, BibTeX, mapping, and review views from curated evidence.

This utility does no discovery or scientific analysis. The registry holds the
manually examined evidence; exports preserve its access limits and wording.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LITERATURE = ROOT / "literature"
REVIEWS = ROOT / "results" / "phase_2" / "individual_paper_reviews.md"
MATRIX_FIELDS = (
    "id", "full_citation", "year", "doi", "url", "categories", "problem",
    "objective", "dataset_location", "dataset_size", "methodology", "algorithms",
    "features", "approach", "baselines", "metrics", "quantitative_results",
    "contributions", "strengths", "limitations", "authors_future_work",
    "dhakanest_relevance", "difference_from_dhakanest", "rq_ids",
    "hypothesis_ids", "comparison_ids", "evidence_access", "source_location",
    "verification_status", "peer_review_status",
)


def citation(paper: dict) -> str:
    return (
        f"{'; '.join(paper['authors'])}, {paper['title']}, "
        f"{paper['venue']}, {paper['year']}."
    )


def csv_text(rows: list[dict], fields) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({
            field: "; ".join(row[field]) if isinstance(row.get(field), list)
            else row.get(field, "Not reported") for field in fields
        })
    return stream.getvalue()


def bib_value(value: str) -> str:
    return value.replace("\\", "\\textbackslash{} ").replace("&", "\\&").replace("%", "\\%")


def bibliography(papers: list[dict]) -> str:
    entries = []
    for paper in papers:
        entry_type = "article" if paper["publication_type"].startswith("journal") else (
            "misc" if paper["publication_type"] == "preprint" else "inproceedings"
        )
        venue_key = "journal" if entry_type == "article" else (
            "howpublished" if entry_type == "misc" else "booktitle"
        )
        fields = {
            "author": " and ".join(paper["authors"]),
            "title": paper["title"], "year": str(paper["year"]),
            venue_key: paper["venue"], "url": paper["url"],
            "note": f"Access: {paper['evidence_access']}; {paper['peer_review_status']}",
        }
        if paper["doi"]:
            fields["doi"] = paper["doi"]
        body = ",\n".join(f"  {key} = {{{bib_value(value)}}}" for key, value in fields.items())
        entries.append(f"@{entry_type}{{{paper['id']},\n{body}\n}}")
    return "\n\n".join(entries) + "\n"


def build_exports(papers: list[dict], additions: list[dict]) -> dict[Path, str]:
    matrix = [{**paper, "full_citation": citation(paper)} for paper in papers]
    screening = [
        {"id": paper["id"], "title": paper["title"], "url": paper["url"],
         "decision": "include", "reason": (
             "Relevant, bibliographic identity checked; substantive full-text review."
             if paper["evidence_access"] == "full_text_examined" else
             "Relevant verified reference; limited access, excluded from deep count."
         )} for paper in papers
    ] + additions
    mappings = []
    for paper in papers:
        for hypothesis_id in paper["hypothesis_ids"]:
            mappings.append({
                "paper_id": paper["id"], "rq_ids": paper["rq_ids"],
                "hypothesis_id": hypothesis_id, "comparison_ids": paper["comparison_ids"],
                "support": paper["dhakanest_relevance"],
                "related_limitation": paper["limitations"],
                "planned_experiment": "Use the linked frozen Phase 1 comparison; this source supplies rationale, not proof of the hypothesis.",
            })
    reviews = [
        "# Individual Paper Reviews\n",
        "Full-text entries examine the cited sections. Limited-access entries are explicitly excluded from the deep-analysis count. Numbers are source-reported and not comparable across datasets.\n",
    ]
    for paper in papers:
        reviews.extend([
            f"## {paper['id']}: {paper['title']}\n",
            f"{citation(paper)}\n",
            f"Access: `{paper['evidence_access']}`. Publication status: `{paper['peer_review_status']}`.\n",
            paper["critical_analysis"] + "\n",
            f"Evidence: [{paper['source_location']}]({paper['url']}). "
            f"Links: {', '.join(paper['rq_ids'] + paper['hypothesis_ids'])}.\n",
        ])
    return {
        LITERATURE / "literature_matrix.csv": csv_text(matrix, MATRIX_FIELDS),
        LITERATURE / "screening_log.csv": csv_text(screening, ("id", "title", "url", "decision", "reason")),
        LITERATURE / "hypothesis_evidence_map.csv": csv_text(mappings, (
            "paper_id", "rq_ids", "hypothesis_id", "comparison_ids", "support",
            "related_limitation", "planned_experiment",
        )),
        LITERATURE / "references.bib": bibliography(papers),
        REVIEWS: "\n".join(reviews),
    }


def main() -> None:
    papers = json.loads((LITERATURE / "paper_registry.json").read_text(encoding="utf-8"))["papers"]
    additions = json.loads((LITERATURE / "screening_additions.json").read_text(encoding="utf-8"))["records"]
    outputs = build_exports(papers, additions)
    # Refuse replacements so a completed phase remains an immutable record.
    existing = [str(path.relative_to(ROOT)) for path in outputs if path.exists()]
    if existing:
        raise FileExistsError(f"Export destinations already exist: {existing}")
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as destination:
            destination.write(content)
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
