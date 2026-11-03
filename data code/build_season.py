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
    data/baselines/hitter_baselines_comprehensive_{year}.parquet
    data/pairs/conditional_lineup_stats_comprehensive_{year}.parquet

The pitch cache must already exist for the season (build it with pull_season.py).
start/end must match the pitch-cache filenames `{bid}_{start}_{end}.parquet`.

`delta_run_exp` in the PA files is only the value of the pitch that ended the PA. The pipeline replaces it with
the value summed over every pitch of the PA (from the pitch cache), so per-PA run value is the full change in
run expectancy across the plate appearance. The terminal-pitch value is kept as `delta_run_exp_last_pitch`.
"""

import argparse
from pathlib import Path

import pandas as pd

from avghitter import hitter_baselines_from_pa_df
from swing_and_battracking_metrics import add_comprehensive_statcast_metrics
from lineup_context import calculate_all_conditional_stats

REPO_ROOT = Path(__file__).parent.parent

def load_team_csvs(team_dir: Path) -> pd.DataFrame:
    frames = []
    for f in sorted(team_dir.glob("*.csv")):
        d = pd.read_csv(f)
        d["team"] = f.stem.upper()
        frames.append(d)
    if not frames:
        raise FileNotFoundError(f"No CSVs found in {team_dir}")
    df = pd.concat(frames, ignore_index=True)
    # 'truncated_pa' rows (a PA cut short by an inning-ending baserunning out, or a walk-off mid-at-bat) are dropped
    # in every season: the batter leads off the next inning, so keeping the row makes him his own predecessor.
    return df[df["events"] != "truncated_pa"].reset_index(drop=True)


def add_full_pa_delta_run_exp(df: pd.DataFrame, cache_dir: Path) -> pd.DataFrame:
    """Replace each PA's delta_run_exp (terminal pitch only) with the sum over every pitch of the PA, from the cache."""
    files = sorted(Path(cache_dir).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No pitch cache files in {cache_dir}")
    pitches = pd.concat([pd.read_parquet(f, columns=["batter", "game_pk", "at_bat_number", "delta_run_exp"])
                         for f in files], ignore_index=True)
    full = (pitches.groupby(["game_pk", "at_bat_number", "batter"], as_index=False)["delta_run_exp"].sum()
            .rename(columns={"delta_run_exp": "delta_run_exp_full_pa"}))
    out = df.merge(full, on=["game_pk", "at_bat_number", "batter"], how="left", validate="many_to_one")
    n_missing = int(out["delta_run_exp_full_pa"].isna().sum())
    if n_missing:
        raise ValueError(f"{n_missing} PAs have no pitches in {cache_dir}; re-pull the season with pull_season.py")
    out["delta_run_exp_last_pitch"] = out["delta_run_exp"]
    out["delta_run_exp"] = out.pop("delta_run_exp_full_pa")
    return out


def build_season(year: int, team_dir: Path, cache_dir: Path,
                 start: str, end: str, tag: str | None = None,
                 min_pairs: int = 30) -> None:
    tag = tag or str(year)   # file label; lets e.g. "2023full" coexist with "2023"
    print(f"[{tag}] loading team CSVs from {team_dir} ...")
    df = load_team_csvs(team_dir)
    print(f"[{year}] {len(df):,} PAs loaded.")
    df = add_full_pa_delta_run_exp(df, cache_dir)
    print(f"[{year}] delta_run_exp set to the full-PA sum from {cache_dir.name}.")

    print(f"[{year}] building baselines + swing/bat-tracking metrics ...")
    baselines = hitter_baselines_from_pa_df(df, min_pa=50)
    baselines = add_comprehensive_statcast_metrics(
        baselines, start=start, end=end, cache_dir=str(cache_dir), progress_every=100
    )
    base_path = REPO_ROOT / "data" / "baselines" / f"hitter_baselines_comprehensive_{tag}.parquet"
    base_path.parent.mkdir(parents=True, exist_ok=True)
    baselines.to_parquet(base_path, index=False)
    print(f"[{year}] saved {base_path.name} ({len(baselines)} hitters)")

    print(f"[{year}] computing conditional lineup stats ...")
    all_conditional = calculate_all_conditional_stats(
        df, baselines, min_conditional_pas=min_pairs, pitch_cache_dir=str(cache_dir),
        start_date=start, end_date=end, include_bat_tracking=True,
    )
    all_conditional["season"] = year
    cond_path = REPO_ROOT / "data" / "pairs" / f"conditional_lineup_stats_comprehensive_{tag}.parquet"
    cond_path.parent.mkdir(parents=True, exist_ok=True)
    all_conditional.to_parquet(cond_path, index=False)
    print(f"[{year}] saved {cond_path.name} ({len(all_conditional)} pairs)")


def main() -> None:
    p = argparse.ArgumentParser(description="Build one season's baseline + conditional tables.")
    p.add_argument("year", type=int)
    p.add_argument("--team-dir", default=None)
    p.add_argument("--cache-dir", default=None)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--tag", default=None,
                   help='Output file label (default: the year), e.g. "2023full"')
    p.add_argument("--min-pairs", type=int, default=30,
                   help="Minimum PAs a (focal, predecessor) pair needs to be kept (>=). Default 30; use 1 to keep every pair.")
    args = p.parse_args()

    d = {}
    team_dir = Path(args.team_dir) if args.team_dir else REPO_ROOT / d.get("team_dir", f"statcast hitters {args.year}")
    cache_dir = Path(args.cache_dir) if args.cache_dir else REPO_ROOT / d.get("cache_dir", f"statcast_pitch_cache_{args.year}")
    start = args.start or d.get("start", f"{args.year}-03-15")
    end = args.end or d.get("end", f"{args.year}-10-05")

    build_season(args.year, team_dir, cache_dir, start, end, args.tag, args.min_pairs)


if __name__ == "__main__":
    main()
