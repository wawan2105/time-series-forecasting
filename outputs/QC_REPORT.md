# Quality-control report — Project 2

Author: Wawan Saputra

- Unit/integrity tests: 4 passed (`test_results.txt`).
- Notebooks: all three executed successfully; outputs embedded in notebook files.
- Public raw snapshots: SHA-256 verified against `data/source_manifest.json`.
- Statistics: reported quantities come from executable analysis; assumptions and limitations are explicit.
- Figures: the main output was visually inspected for readability.
- Reproducibility: Python and direct package versions recorded; no invented metrics or conclusions.
- CV bullets: generated from actual results in the executive summary.

## Method-specific review

Expanding time splits precede test years. Annual data receive no invented seasonal period. Model selection uses rolling-origin RMSE; final holdout is separate. Future output is explicitly retrospective from 2024. Point forecasts for ETS have no fabricated confidence interval.
