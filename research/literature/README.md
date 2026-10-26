# Literature Evidence

Phase 2 uses a curated registry plus reproducible views. Start with
`paper_registry.json`; `literature_matrix.csv` provides the full evidence fields
for spreadsheet review. The generated individual reviews are in
`../results/phase_2/individual_paper_reviews.md`.

- `search_protocol.json`: date, facilities, queries, criteria and limitations.
- `screening_log.csv`: every deliberately assessed candidate and its decision.
- `screening_additions.json`: deferred/excluded candidates outside the registry.
- `hypothesis_evidence_map.csv`: actual Phase 1 hypothesis and comparison IDs.
- `references.bib`: registry-consistent bibliography; preprints are labeled.
- `export_literature.py`: deterministic views; refuses to overwrite outputs.
- `validate_literature.py`: offline identity, access, linkage, and export checks.

From the repository root:

```powershell
backend\.venv\Scripts\python.exe -m research.literature.validate_literature
backend\.venv\Scripts\python.exe -m unittest discover -s research\tests -v
```

Validation does not independently verify science or resolve every DOI online.
The cited source locations and recorded access level carry that evidence.
`full_text_examined` means pertinent sections were inspected; limited-access
entries never count toward the minimum 25 substantive reviews.

For a future update, create a new version/destination and retain this phase's
registry and manifest. Do not rerun the exporter over the frozen results.
