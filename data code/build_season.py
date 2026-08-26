# -*- coding: utf-8 -*-
"""
Parameterized single-season build: turns one season's team CSVs + pitch cache
into that season's baseline + conditional-pair tables. Generalizes what
run_analysis.py + lineup_extract.py do for 2025, so any year can be built.

Usage:
    python build_season.py 2024
    python build_season.py 2025 --team-dir "statcast hitters" \
        --cache-dir statcast_pitch_cache_2025 --start 2025-03-18 --end 2025-09-28

Outputs (in the repo root):
    hitter_baselines_comprehensive_{year}.parquet
    conditional_lineup_stats_comprehensive_{year}.parquet

The pitch cache must already exist for the season (build it with pull_season.py).
start/end must match the pitch-cache filenames `{bid}_{start}_{end}.parquet`.
"""

import argparse
from pathlib import Path

import pandas as pd

from avghitter import hitter_baselines_from_pa_df
from swing_and_battracking_metrics import add_comprehensive_statcast_metrics
from lineup_context import calculate_all_conditional_stats

REPO_ROOT = Path(__file__).parent.parent

# Per-season defaults. 2025 was manually downloaded (statcast hitters/, RS range
# 03-18..09-28); later seasons come from pull_season.py (statcast hitters {yr}/,
# default range 03-15..10-05).
SEASON_DEFAULTS = {
    2025: dict(team_dir="statcast hitters", cache_dir="statcast_pitch_cache_2025",
               start="2025-03-18", end="2025-09-28"),
}


def load_team_csvs(team_dir: Path) -> pd.DataFrame:
    frames = []
    for f in sorted(team_dir.glob("*.csv")):
        d = pd.read_csv(f)
        d["team"] = f.stem.upper()
        frames.append(d)
    if not frames:
        raise FileNotFoundError(f"No CSVs found in {team_dir}")
    return pd.concat(frames, ignore_index=True)


def build_season(year: int, team_dir: Path, cache_dir: Path,
                 start: str, end: str) -> None:
    print(f"[{year}] loading team CSVs from {team_dir} ...")
    df = load_team_csvs(team_dir)
    print(f"[{year}] {len(df):,} PAs loaded.")

    print(f"[{year}] building baselines + swing/bat-tracking metrics ...")
    baselines = hitter_baselines_from_pa_df(df, min_pa=50)
    baselines = add_comprehensive_statcast_metrics(
        baselines, start=start, end=end, cache_dir=str(cache_dir), progress_every=100
    )
    base_path = REPO_ROOT / f"hitter_baselines_comprehensive_{year}.parquet"
    baselines.to_parquet(base_path, index=False)
    print(f"[{year}] saved {base_path.name} ({len(baselines)} hitters)")

    print(f"[{year}] computing conditional lineup stats ...")
    all_conditional = calculate_all_conditional_stats(
        df, baselines, min_conditional_pas=30, pitch_cache_dir=str(cache_dir),
        start_date=start, end_date=end, include_bat_tracking=True,
    )
    all_conditional["season"] = year
    cond_path = REPO_ROOT / f"conditional_lineup_stats_comprehensive_{year}.parquet"
    all_conditional.to_parquet(cond_path, index=False)
    print(f"[{year}] saved {cond_path.name} ({len(all_conditional)} pairs)")


def main() -> None:
    p = argparse.ArgumentParser(description="Build one season's baseline + conditional tables.")
    p.add_argument("year", type=int)
    p.add_argument("--team-dir", default=None)
    p.add_argument("--cache-dir", default=None)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    args = p.parse_args()

    d = SEASON_DEFAULTS.get(args.year, {})
    team_dir = Path(args.team_dir) if args.team_dir else REPO_ROOT / d.get("team_dir", f"statcast hitters {args.year}")
    cache_dir = Path(args.cache_dir) if args.cache_dir else REPO_ROOT / d.get("cache_dir", f"statcast_pitch_cache_{args.year}")
    start = args.start or d.get("start", f"{args.year}-03-15")
    end = args.end or d.get("end", f"{args.year}-10-05")

    build_season(args.year, team_dir, cache_dir, start, end)


if __name__ == "__main__":
    main()
