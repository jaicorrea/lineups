# -*- coding: utf-8 -*-
"""
Pool multiple seasons' conditional-pair tables into one stacked dataset for
regression. Each (focal, conditional) pair from each season is one row (a
season column distinguishes them), so a pair that co-occurred in both seasons
contributes two observations -- roughly doubling N and giving the split-half /
high-PA-cutoff checks real statistical power.

Applies the same Nitro_med_xy unpacking + nitro_dist derivation as
tablesort_scratch.py, and writes a single pooled CSV.

Usage:
    python pool_seasons.py 2024 2025
    python pool_seasons.py 2024 2025 --out conditional_stats_with_baselines_pooled.csv
"""

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent


def _nitro_component(value, index):
    if value is None:
        return pd.NA
    try:
        component = value[index]
    except (TypeError, IndexError):
        return pd.NA
    return pd.NA if component is None else float(component)


def load_season(year: int) -> pd.DataFrame:
    path = REPO_ROOT / "data code" / f"conditional_lineup_stats_comprehensive_{year}.parquet"
    if not path.exists():
        path = REPO_ROOT / f"conditional_lineup_stats_comprehensive_{year}.parquet"
    df = pd.read_parquet(path)
    if "season" not in df.columns:
        df["season"] = year
    return df


def pool_seasons(years: list[int], out_name: str) -> None:
    frames = [load_season(y) for y in years]
    for y, f in zip(years, frames):
        print(f"  {y}: {len(f):,} pairs, {len(f.columns)} cols")
    out = pd.concat(frames, ignore_index=True)
    print(f"Pooled: {len(out):,} pairs across seasons {years}")

    # Unpack Nitro_med_xy tuples -> numeric x/z columns
    for prefix in ["focal_season", "conditional_season", "focal", "conditional"]:
        col = f"{prefix}_Nitro_med_xy"
        if col in out.columns:
            out[f"{prefix}_nitro_x"] = out[col].apply(lambda v: _nitro_component(v, 0))
            out[f"{prefix}_nitro_z"] = out[col].apply(lambda v: _nitro_component(v, 1))

    out["nitro_dist"] = (
        (out["focal_season_nitro_x"] - out["conditional_season_nitro_x"]) ** 2
        + (out["focal_season_nitro_z"] - out["conditional_season_nitro_z"]) ** 2
    ) ** 0.5

    # Column order: non-prefixed (num_PAs, season, nitro_dist), focal, conditional
    focal_cols = [c for c in out.columns if c.startswith("focal_")]
    conditional_cols = [c for c in out.columns if c.startswith("conditional_")]
    other_cols = [c for c in out.columns if not c.startswith("focal_") and not c.startswith("conditional_")]
    out = out[other_cols + focal_cols + conditional_cols]

    out_path = REPO_ROOT / out_name
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out):,} rows x {len(out.columns)} cols -> {out_path.name}")
    print(f"nitro_dist non-null: {out['nitro_dist'].notna().sum()} / {len(out)}")
    print(f"season counts: {out['season'].value_counts().to_dict()}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("years", type=int, nargs="+")
    p.add_argument("--out", default="conditional_stats_with_baselines_pooled.csv")
    args = p.parse_args()
    pool_seasons(args.years, args.out)


if __name__ == "__main__":
    main()
