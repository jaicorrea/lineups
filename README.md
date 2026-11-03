# lineups

Do hitters perform differently depending on the style of the hitter who bats just before them? This repo tests lineup complementarities in MLB: whether the *type* of hitter ahead of a batter (swing, bat-tracking and batted-ball traits) changes that batter's Barrel/PA or run value per PA.

Sample: regular-season plate appearances for the 2025 and 2026 seasons (2026 is complete through 2026-09-27).

## Design in one paragraph

Each observation is a (focal hitter, predecessor) pair within a season. Traits are season-long hitter averages, z-scored within season. Each test regresses the focal hitter's outcome in those pairs on `predecessor trait x focal trait` with focal-hitter-by-season and predecessor-by-season fixed effects (so only which pairings formed within a season identifies the interaction), weighted by the number of PAs in the pair and clustered on the focal hitter (team-season and two-way clustering are also reported). Outcomes: Barrel/PA (primary) and run value per PA (secondary). Eleven pre-specified interactions are tested with a Holm correction. The same eleven are also run in the reverse direction, with the predecessor's own run value per PA (in the PAs where the focal hitter batted behind him) as the outcome. Five post hoc production-trait interactions (OBP, SLG, BA, Barrel/PA, BB%, K%, K-BB%) are run on all three outcomes.

## Repository structure

### `data code/` — pipeline
Run in this order for each season (see each script's docstring / `--help` for options):

| Step | Script | What it does |
|---|---|---|
| 1 | `pull_season.py` | Pulls a regular season from Baseball Savant (pybaseball) and writes per-team PA CSVs plus a per-batter pitch-level cache |
| 2 | `build_season.py` | Builds season baselines (`avghitter.py`, `swing_and_battracking_metrics.py`) and every predecessor/focal pair (`lineup_context.py`); writes `data/pairs/conditional_lineup_stats_comprehensive_{tag}.parquet` and `data/baselines/hitter_baselines_comprehensive_{tag}.parquet` |
| 3 | `pool_seasons.py` | Stacks the seasons into `data/pooled/conditional_stats_with_baselines_pooled_all.csv` |
| 4 | `attach_team.py` | Adds each pair's `team` and a cross-team flag -> `data/pooled/conditional_stats_with_baselines_pooled_all_team.csv` |
| 5 | `build_kbb_traits.py` | Computes season BB%, K% and K-BB% per hitter and side from the PA files -> `analysis/kbb_traits.csv` (needed only for `production_tests.R`) |

The analysis data were built with `build_season.py <year> --tag <year>_all --min-pairs 1` (every pair kept, no minimum PAs per pair), then `pool_seasons.py 2025_all 2026_all --out conditional_stats_with_baselines_pooled_all.csv`.

Pairing rule (`lineup_context.py`): the predecessor is the previous batter *on the same team in the same game*, so the first batter of an inning is paired with his own team's last batter from the previous inning. Barrel is Statcast's own classification (`launch_speed_angle == 6`). Swing and bat-tracking metrics use regular-season pitches only.

**Run value per PA is the full-PA run expectancy change.** The `delta_run_exp` in the PA files is only the value of the pitch that ended the PA. `build_season.py` replaces it with the sum over every pitch of the PA, taken from the pitch cache (`add_full_pa_delta_run_exp`), so a PA's run value is its end-of-PA run expectancy minus the run expectancy of the state the hitter inherited (base-out state and a 0-0 count), including the value of the count he built. The terminal-pitch value is kept as `delta_run_exp_last_pitch`. The build stops with an error if any PA has no pitches in the cache. This applies to the pair outcomes (`focal_delta_run_exp_PA`, `conditional_delta_run_exp_PA`) and to the hitter-level `delta_run_exp_PA` baseline trait.

**Truncated PAs are disregarded in every season.** Statcast's `events == 'truncated_pa'` rows (a plate appearance cut short, almost always by a third-out baserunning play such as a caught stealing, and in two 2025 cases a walk-off mid-at-bat) are dropped before any pairing, baseline, team or K/BB calculation (`build_season.py`, `attach_team.py`, `build_team_lookup.py`, `build_kbb_traits.py`, `trait_reliability.py`). They are dropped so that no hitter is his own predecessor: the batter leads off the next inning, so keeping the row paired him with himself (213 self-pairs in 2026 before the filter). The original hand-downloaded 2025 files never contained these rows, but the pulled seasons do (319 in 2025 and 329 in 2026), so the filter is applied to both seasons to keep them consistent. The 2026 raw PA files are left as Savant delivered them; the 2025 PA files were filtered when they were set up (see below). In every season the pitches from truncated PAs still count toward the season swing and bat-tracking baselines (the pitch caches are not filtered).

Earlier-iteration (2025-only) scripts still in this folder and not used for the current results: `statcast_research.py`, `run_analysis.py`, `lineup_extract.py`, `research_scratch.py`, `tablesort_scratch.py`, `swing_pct_statcast.py`.

### `analysis/` — final analysis
| File | Purpose |
|---|---|
| `all11.R` | The 11 pre-specified interactions on the pooled data; writes `all11_pooled.csv` and `all11_by_season.csv`. Run `Rscript all11.R <pooled csv> cond` for the reverse-direction version (outcome = predecessor's run value per PA), which writes `all11_cond_pooled.csv` and `all11_cond_by_season.csv` |
| `production_tests.R` | Five post hoc production interactions (cond OBP x focal SLG, cond Barrel/PA x focal BB%, cond K% x focal BB%, cond K-BB% x focal Barrel/PA, cond OBP x focal BA) on focal Barrel/PA, focal run value and predecessor run value; writes `production_pooled.csv` and `production_by_season.csv` |
| `kbb_traits.csv` | Season-level BB%, K% and K-BB% per hitter and batting side, built by `data code/build_kbb_traits.py` from the PA files (read by `production_tests.R`) |
| `trait_reliability.py` -> `trait_reliability.csv` | Odd/even PA split-half reliability (Spearman-Brown) of each trait |
| `reducedformregs2.do`, `reducedformregs2.R` | Stata specification from the project's advisor (2025-only, run-value models 1-9) and its R translation (output files are not tracked) |
| `regressions.do`, `regressions.R` | Second Stata specification from the advisor and its R translation (output files are not tracked) |

The two `.do` files run on the 2025 pair file (`conditional_lineup_stats_2025.csv`, `conditional_stats_with_baselines.csv`). Both are built with the current pairing rule and minimum of 30 PAs per pair. The advisor's original results were computed on an earlier version of that file that used a different pairing rule, so the numbers here do not match his.

### Data files (root)
- `data/pooled/conditional_stats_with_baselines_pooled_all_team.csv` — analysis dataset: one row per (season, focal hitter, predecessor) pair, with both hitters' season baselines and the focal hitter's outcomes in those pairs.
- `data/pairs/conditional_lineup_stats_comprehensive_{2025,2026}_all.parquet` and `data/baselines/hitter_baselines_comprehensive_{2025,2026}_all.parquet` — per-season outputs of step 2.
- `data/pooled/conditional_stats_with_baselines_pooled_all.csv` — step 3 output, before the team columns are attached.
- `data/team_lookup.csv` — each hitter's team per season (`build_team_lookup.py`).
- `conditional_lineup_stats_2025.csv`, `conditional_stats_with_baselines.csv` — 2025-only pair data used by the `.do` files.

## Getting the raw data

The raw data are not in the repo (about 1 GB). Regenerate them with pybaseball (internet access required; roughly 15-40 minutes per season):

```
cd "data code"
python pull_season.py 2025
python pull_season.py 2026
```

By default this writes the per-team PA CSVs to `statcast hitters {year}/` and the per-batter pitch-level parquets to `statcast_pitch_cache_{year}/` at the repo root. Both seasons are pulled this way. 2025 was originally downloaded by hand from Baseball Savant; that download is kept as `statcast hitters 2025 manual/`, and `pull_season.py` reads it as the column-schema reference. Compared with that download the 2025 pull has the same 118 columns and the same PAs, plus 319 truncated PAs and 34 other PAs (25 intentional walks, 8 catcher-interference PAs, 1 strikeout) that the manual download lacked. `statcast hitters 2025/` has all of those removed, so it holds exactly the 182,892 PAs of the manual download, with values from the pull. Savant's later revisions leave small differences in some fields (for example `plate_x`/`plate_z` by about 0.0025 and `woba_denom`, blank on 531 intentional walks where the manual files had 0). The pull is re-run with `python pull_season.py 2025`, then those PAs are removed, to reproduce the folder. Then build and pool as described above (`build_season.py` takes `--team-dir` and `--cache-dir` if your folders are named differently).

These folders are listed in `.gitignore`. Note that a fresh Savant pull can differ slightly from the files used here if Savant has revised data since.

## Requirements
- Python 3: pandas, numpy, pyarrow, pybaseball
- R 4.4: fixest, dplyr, readr. Run `all11.R` with a single fixest thread (the script sets this); multithreaded fixest crashed on this data on Windows.
- Stata with `reghdfe` for the `.do` files (optional; the `.R` files reproduce them)
