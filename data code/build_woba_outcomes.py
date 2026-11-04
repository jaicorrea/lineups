# -*- coding: utf-8 -*-
"""
Build pair-level wOBA and xwOBA outcomes and attach them to the pooled pair table.

SEPARATE from the existing pipeline: nothing in lineup_context.py or the existing
parquet/CSV outputs is modified. The pairing uses the SAME function the pipeline uses
(get_actual_before_after_batters, same-team batting order), so every pair lines up with
the existing table; the script verifies that PA counts match for every merged pair.

Pair outcomes (per season, focal hitter f, prior hitter c, sides as in the pipeline):
    woba_pair  = sum(woba_value)                    / sum(woba_denom)
    xwoba_pair = sum(estimated_woba_using_speedangle) / sum(woba_denom)
where PAs with woba_denom == 0 (intentional walks, sac bunts) or a missing denominator
are excluded from both numerator and denominator. In the PA files the expected-wOBA
column already carries Statcast's xwOBA-style value for every PA type (0 for strikeouts,
~.69 for walks, expected value from exit velo/launch angle on balls in play); where it is
missing on a counted PA the actual wOBA value is used.

Usage:
    python build_woba_outcomes.py
    python build_woba_outcomes.py --pooled data/pooled/conditional_stats_with_baselines_pooled_all_team.csv \
        --out data/pooled/conditional_stats_with_woba_pooled_all_team.csv
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lineup_context import get_actual_before_after_batters  # same pairing as the pipeline

REPO_ROOT = Path(__file__).parent.parent

# season -> folder of PA-level team CSVs
SEASON_DIRS = {
    2025: "statcast hitters 2025",
    2026: "statcast hitters 2026",
}
USECOLS = ["events", "game_pk", "at_bat_number", "batter", "stand", "inning_topbot", "home_team",
           "away_team", "woba_value", "woba_denom", "estimated_woba_using_speedangle"]
# The PA files carry Statcast's rounded woba_value (1B .9, BB .7, HR 2.0, reached-on-error as a hit), which
# overstates wOBA by ~.012 vs the Savant leaderboard. Rebuild the value from the event with unrounded linear
# weights (validated against Savant 2025 for the 40 most-PA hitters: mean diff -.0004, max .002).
WOBA_W = {"walk": 0.69, "hit_by_pitch": 0.72, "single": 0.88, "double": 1.247, "triple": 1.578, "home_run": 2.031}
KEYS = ["season", "focal_batter_id", "focal_HitterSide",
        "conditional_batter_id", "conditional_HitterSide"]


def season_pair_outcomes(season: int, folder: str) -> pd.DataFrame:
    frames = [pd.read_csv(f, usecols=USECOLS) for f in sorted((REPO_ROOT / folder).glob("*.csv"))]
    pa = pd.concat(frames, ignore_index=True)
    pa["woba_value"] = pa["events"].map(WOBA_W).fillna(0.0)
    d = get_actual_before_after_batters(pa)
    d = d.dropna(subset=["batter_before", "stand_before"]).copy()

    den = d["woba_denom"].fillna(0)
    counted = den > 0
    d["_den"] = den.where(counted, 0.0)
    d["_w"] = d["woba_value"].where(counted, 0.0)
    xw = d["estimated_woba_using_speedangle"].fillna(d["woba_value"])
    d["_x"] = xw.where(counted, 0.0)

    g = (d.groupby(["batter", "stand", "batter_before", "stand_before"])
           .agg(n_pa_check=("batter", "size"), woba_den=("_den", "sum"),
                w_num=("_w", "sum"), x_num=("_x", "sum"))
           .reset_index()
           .rename(columns={"batter": "focal_batter_id", "stand": "focal_HitterSide",
                            "batter_before": "conditional_batter_id",
                            "stand_before": "conditional_HitterSide"}))
    g["conditional_batter_id"] = g["conditional_batter_id"].astype("int64")
    g["focal_batter_id"] = g["focal_batter_id"].astype("int64")
    g["woba_pair"] = g["w_num"] / g["woba_den"].where(g["woba_den"] > 0)
    g["xwoba_pair"] = g["x_num"] / g["woba_den"].where(g["woba_den"] > 0)
    g["season"] = season
    return g.drop(columns=["w_num", "x_num"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pooled", default="data/pooled/conditional_stats_with_baselines_pooled_all_team.csv")
    p.add_argument("--out", default="data/pooled/conditional_stats_with_woba_pooled_all_team.csv")
    args = p.parse_args()

    pooled = pd.read_csv(REPO_ROOT / args.pooled)
    seasons = sorted(pooled["season"].unique())
    outs = []
    for s in seasons:
        print(f"[{s}] building pair wOBA/xwOBA from {SEASON_DIRS[s]} ...")
        outs.append(season_pair_outcomes(s, SEASON_DIRS[s]))
    woba = pd.concat(outs, ignore_index=True)

    pooled["conditional_batter_id"] = pooled["conditional_batter_id"].astype("int64")
    merged = pooled.merge(woba, on=KEYS, how="left", validate="one_to_one")

    # ---- checks ----
    unmatched = merged["n_pa_check"].isna().sum()
    mism = (merged["n_pa_check"] != merged["num_PAs"]) & merged["n_pa_check"].notna()
    print(f"\nPairs in pooled table: {len(pooled):,} | unmatched to wOBA table: {unmatched}")
    print(f"PA-count mismatches vs existing num_PAs: {int(mism.sum())}")
    lost = 1 - merged["woba_den"].sum() / merged["num_PAs"].sum()
    print(f"Share of PAs excluded from wOBA (zero/missing denominator): {lost:.2%}")
    print("\nOutcome summary (pairs):")
    print(merged[["woba_pair", "xwoba_pair", "focal_delta_run_exp_PA"]].describe().round(3).to_string())
    print("\nCorrelation of pair outcomes:")
    print(merged[["woba_pair", "xwoba_pair", "focal_delta_run_exp_PA"]].corr().round(3).to_string())

    merged["woba_pa_mismatch"] = mism.astype(int)
    merged = merged.drop(columns=["n_pa_check"])
    merged.to_csv(REPO_ROOT / args.out, index=False)
    print(f"\nWrote {len(merged):,} rows x {len(merged.columns)} cols -> {args.out}")


if __name__ == "__main__":
    main()
