# -*- coding: utf-8 -*-
"""
Pull a full regular season of PA-level Statcast data from Baseball Savant and
write it out in the same per-team CSV format as the manually-downloaded files
in `statcast hitters/` (which are 2025).

Usage:
    python pull_season.py 2024
    python pull_season.py 2024 --start 2024-03-20 --end 2024-09-29
    python pull_season.py 2024 --out-dir "statcast hitters 2024"
    python pull_season.py 2024 --no-cache        # skip the pitch cache

Produces TWO things from a single league-wide pull:
  1. PA-level team CSVs (like the manually-downloaded `statcast hitters/` files)
     -> used for BA/OBP/SLG, barrels, nitro zone, delta_run_exp.
  2. Per-batter pitch-level cache in `statcast_pitch_cache_{year}/`
     -> used by the swing / bat-tracking metrics (Swing%, Contact%, SwStr%,
     Chase%, SweetSpot%, batted-ball %s, attack angle / direction / swing tilt).
     Files are named `{player_id}_{start}_{end}.parquet`, matching what
     `add_comprehensive_statcast_metrics` expects (pass the SAME start/end
     downstream so the cache is found).

Notes
-----
* pybaseball.statcast() returns PITCH-level data for the whole league. The
  existing team CSVs are PA-level (one row per plate appearance, the pitch that
  ended the PA). We reproduce that by keeping only rows with a terminal `events`
  value, then de-duplicating on (game_pk, at_bat_number). The pitch cache is
  built from the full (pre-collapse) regular-season pitch data.
* Only regular-season games (game_type == 'R') are kept, matching the existing
  files.
* Each row's *batting* team is the away team in the top of the inning and the
  home team in the bottom; files are named by the batting team using the same
  abbreviations as the existing folder (note TB->tbr, KC->kcr, WSH->was).
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Savant team code -> existing filename stem. Anything not listed is just
# lower-cased (ATH->ath, AZ->az, CWS->cws, LAD->lad, ...).
TEAM_FILENAME_OVERRIDES = {
    "TB": "tbr",
    "KC": "kcr",
    "WSH": "was",
}

REPO_ROOT = Path(__file__).parent.parent
REFERENCE_TEAM_DIR = REPO_ROOT / "statcast hitters"  # 2025, for canonical schema


def savant_code_to_stem(code: str) -> str:
    return TEAM_FILENAME_OVERRIDES.get(code, code.lower())


def reference_columns() -> list[str] | None:
    """Column order of the existing team CSVs, so new files match exactly."""
    sample = next(REFERENCE_TEAM_DIR.glob("*.csv"), None)
    if sample is None:
        return None
    return pd.read_csv(sample, nrows=0).columns.tolist()


def build_pitch_cache(raw: pd.DataFrame, start: str, end: str, cache_dir: Path) -> None:
    """Write per-batter pitch-level parquet files, matching the layout that
    `add_comprehensive_statcast_metrics` reads (`{bid}_{start}_{end}.parquet`).
    Built from the full regular-season pitch data (before the PA collapse)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    batters = raw["batter"].dropna().astype("int64").unique()
    for i, bid in enumerate(batters, start=1):
        sub = raw[raw["batter"] == bid]
        sub.to_parquet(cache_dir / f"{bid}_{start}_{end}.parquet", index=False)
        if i % 100 == 0 or i == len(batters):
            print(f"  cached {i}/{len(batters)} batters")
    print(f"Wrote {len(batters)} per-batter pitch files to {cache_dir}")


def pull_season(year: int, start: str, end: str, out_dir: Path,
                cache_dir: Path | None) -> None:
    from pybaseball import statcast

    print(f"Pulling pitch-level Statcast for {start} -> {end} "
          f"(this can take 15-40 min for a full season)...")
    raw = statcast(start_dt=start, end_dt=end)
    print(f"  Pulled {len(raw):,} pitch-level rows.")

    # statcast() concatenates daily chunks WITHOUT resetting the index, so index
    # labels repeat across days. Reset to a clean unique index -- otherwise any
    # later .loc[index] selection explodes rows on duplicate labels.
    raw = raw.reset_index(drop=True)

    # Regular season only
    if "game_type" in raw.columns:
        raw = raw[raw["game_type"] == "R"]
        print(f"  {len(raw):,} rows after regular-season (game_type=='R') filter.")

    # Per-batter pitch cache (built from the full pitch-level data)
    if cache_dir is not None:
        print("\nBuilding per-batter pitch cache...")
        build_pitch_cache(raw, start, end, cache_dir)
        print()

    # Collapse pitch-level -> PA-level: keep the terminal pitch of each PA
    pa = raw[raw["events"].notna()].copy()
    pa = pa.drop_duplicates(subset=["game_pk", "at_bat_number"], keep="last")
    print(f"  {len(pa):,} plate appearances after collapsing to PA level.")

    # IMPORTANT: statcast()'s `player_name` is the PITCHER, not the batter. The
    # manually-downloaded batter exports use the BATTER's name, so remap it to
    # the batter (by MLBAM id) to keep the two data sources consistent.
    try:
        from pybaseball import playerid_reverse_lookup
        ids = pa["batter"].dropna().astype("int64").unique().tolist()
        look = playerid_reverse_lookup(ids, key_type="mlbam")
        name_map = {
            int(r["key_mlbam"]): f"{str(r['name_last']).title()}, {str(r['name_first']).title()}"
            for _, r in look.iterrows()
        }
        pa["player_name"] = pa["batter"].astype("int64").map(name_map)
        print(f"  Remapped player_name to batter for {len(name_map)} batters.")
    except Exception as e:  # non-fatal: names are labels, not used in analysis
        print(f"  [WARN] could not remap player_name to batter: {e}")

    # Batting team: away in top of inning, home in bottom
    top = pa["inning_topbot"].astype(str).str.lower().str.startswith("top")
    pa["batting_team"] = pa["home_team"].where(~top, pa["away_team"])

    # Match the existing column schema where possible (keeps downstream identical)
    ref_cols = reference_columns()
    if ref_cols is not None:
        keep = [c for c in ref_cols if c in pa.columns]
        pa_out = pa.reindex(columns=keep)
    else:
        pa_out = pa

    out_dir.mkdir(parents=True, exist_ok=True)
    n_files = 0
    for code, grp in pa.groupby("batting_team"):
        stem = savant_code_to_stem(str(code))
        rows = pa_out.loc[grp.index]
        rows.to_csv(out_dir / f"{stem}.csv", index=False)
        n_files += 1
    print(f"\nWrote {n_files} team files to {out_dir}")
    print(f"Total PAs: {len(pa):,}  |  Unique batters: {pa['batter'].nunique()}")


def main() -> None:
    p = argparse.ArgumentParser(description="Pull a regular season of PA-level Statcast data.")
    p.add_argument("year", type=int, help="Season year, e.g. 2024")
    p.add_argument("--start", default=None, help="Start date YYYY-MM-DD (default: {year}-03-15)")
    p.add_argument("--end", default=None, help="End date YYYY-MM-DD (default: {year}-10-05)")
    p.add_argument("--out-dir", default=None,
                   help='Team-CSV output folder (default: "statcast hitters {year}")')
    p.add_argument("--cache-dir", default=None,
                   help='Pitch-cache folder (default: "statcast_pitch_cache_{year}")')
    p.add_argument("--no-cache", action="store_true",
                   help="Skip building the per-batter pitch cache")
    args = p.parse_args()

    start = args.start or f"{args.year}-03-15"
    end = args.end or f"{args.year}-10-05"
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / f"statcast hitters {args.year}"
    if args.no_cache:
        cache_dir = None
    else:
        cache_dir = Path(args.cache_dir) if args.cache_dir else REPO_ROOT / f"statcast_pitch_cache_{args.year}"

    pull_season(args.year, start, end, out_dir, cache_dir)


if __name__ == "__main__":
    main()
