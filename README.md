# lineups

Finding hitter complementarities in lineups to create an optimized sequencing of hitters.

## Repository Structure

### `data code/`
Nine Python scripts for pulling, processing, and analyzing Statcast data.

| File | Purpose |
|------|---------|
| `statcast_research.py` | Loads all 30 team CSVs from `statcast hitters/` into a single PA-level DataFrame |
| `avghitter.py` | Computes per-hitter baseline stats (BA, OBP, SLG, Barrel/PA, Pitch/PA, Nitro Zone) from PA-level data |
| `swing_and_battracking_metrics.py` | Calculates comprehensive Statcast metrics: Swing%, Contact%, SwStr%, Chase%, Sweet Spot%, bat tracking (Attack Angle, Stance Angle, etc.) |
| `swing_pct_statcast.py` | Earlier version of swing/bat tracking metrics module |
| `run_analysis.py` | Entry point: builds hitter baselines and adds all Statcast metrics, saves `hitter_baselines_comprehensive.parquet` |
| `lineup_context.py` | Core analysis — calculates each batter's stats conditional on who batted immediately before them |
| `lineup_extract.py` | Runs the full conditional stats pipeline for all batter pairs, saves `conditional_lineup_stats_comprehensive_2025.parquet` |
| `research_scratch.py` | Scratch script for exploring baseline and conditional stats outputs |
| `tablesort_scratch.py` | Merges conditional lineup stats with season-long baselines and exports to CSV |

### `statcast hitters/`
30 CSV files (one per MLB team) with PA-level Statcast data for 2025. Each file is named by team abbreviation (e.g., `lad.csv`, `nyy.csv`).

### `statcast_pitch_cache_2025/`
532 parquet files with pitch-level Statcast data for individual batters (2025 season, March 18 – September 28). Files are named `{player_id}_2025-03-18_2025-09-28.parquet`. Used as a cache by the swing/bat tracking metrics scripts to avoid repeated API calls.

### `conditional_lineup_stats_2025.csv`
Output table with each batter's performance stats broken down by who batted immediately before them in the lineup. One row per focal batter / conditional batter pair.

## How It Works

1. **Load PA data** — `statcast_research.py` reads the 30 team CSVs and combines them into a single DataFrame.
2. **Build baselines** — `run_analysis.py` computes season-long stats for each hitter (BA, OBP, SLG, Barrel/PA, Swing%, etc.) and caches individual pitch files to `statcast_pitch_cache_2025/`.
3. **Conditional analysis** — `lineup_extract.py` runs `lineup_context.calculate_all_conditional_stats()`, which groups each batter's PAs by who batted before them and computes conditional vs. season-long stat differences.
4. **Explore results** — `research_scratch.py` and `tablesort_scratch.py` are used to query and export results.
