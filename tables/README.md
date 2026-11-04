# Paper tables

One `.tex` file per table in `paper/main.tex` (pulled in with `\input`). Do not edit these by hand: rerun the script that makes them (`make_all.ps1` runs everything).

| File | Paper table | Made by |
|---|---|---|
| `pair_pa_distribution.tex` | Distribution of pairs by PAs per pair | `analysis/paper_tables.R` |
| `pair_side_composition.tex` | Sample by pair handedness | `analysis/paper_tables.R` |
| `proxy_regressions.tex` | Barrel/PA and wOBA as proxies for run expectancy | `analysis/proxy_regressions.R all` -> `paper_tables.R` |
| `trait_reliability.tex` | Split-half reliability of traits | `analysis/trait_reliability.py` -> `paper_tables.R` |
| `expected_signs_focal.tex`, `expected_signs_cond.tex` | Expected sign of the interaction (appendix) | `analysis/paper_tables.R` |
| `interaction_focal_{2025,2026}.tex` | beta_3 on focal hitter's delta run expectancy | `analysis/table1_regressions.R` -> `paper_tables.R` |
| `interaction_cond_{2025,2026}.tex` | beta_3 on conditional hitter's delta run expectancy | `analysis/table1_regressions.R` -> `paper_tables.R` |
| `interaction_barrel_{2025,2026}.tex` | beta_3 on focal hitter's Barrel/PA | `analysis/table1_regressions.R` -> `paper_tables.R` |

`paper_tables.R` reads the regression outputs that `table1_regressions.R` and `proxy_regressions.R` write into `analysis/` and re-labels the captions to match the paper (for example ", 2025" and "$\Delta$ Run Expectancy").

The tables need `booktabs`, `float` and `amssymb` in the LaTeX preamble (already in `paper/main.tex`).
