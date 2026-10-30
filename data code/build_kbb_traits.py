# -*- coding: utf-8 -*-
"""
Season-level BB%, K% and K-BB% per (season, batter, batting side), from the PA-level
team CSVs. Written to analysis/kbb_traits.csv for analysis/production_tests.R.
Keyed the same way as the hitter baselines (batter + HitterSide), PA = every PA row.
BB includes intentional walks (as in OBP elsewhere in the pipeline).
"""
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
SEASON_DIRS = {2023: "statcast hitters 2023", 2024: "statcast hitters 2024",
               2025: "statcast hitters", 2026: "statcast hitters 2026"}
K = {"strikeout", "strikeout_double_play"}
BB = {"walk", "intent_walk"}

out = []
for season, folder in SEASON_DIRS.items():
    df = pd.concat([pd.read_csv(f, usecols=["game_date", "batter", "stand", "events"])
                    for f in sorted((REPO_ROOT / folder).glob("*.csv"))], ignore_index=True)
    df = df[df["events"].notna()]
    df["K"] = df["events"].isin(K).astype(int)
    df["BB"] = df["events"].isin(BB).astype(int)
    g = df.groupby(["batter", "stand"]).agg(PA=("K", "size"), K=("K", "sum"), BB=("BB", "sum")).reset_index()
    g["season"] = season
    g["BB_pct"], g["K_pct"] = g["BB"] / g["PA"], g["K"] / g["PA"]
    g["KBB_pct"] = g["K_pct"] - g["BB_pct"]
    print(season, folder, df["game_date"].min(), df["game_date"].max(), len(g), "batter-sides")
    out.append(g)
res = pd.concat(out, ignore_index=True)

# sanity check against the baselines' PA counts
chk = []
for season in SEASON_DIRS:
    b = pd.read_parquet(REPO_ROOT / f"hitter_baselines_comprehensive_{season}_all.parquet", columns=["batter", "HitterSide", "PA"])
    m = b.merge(res[res.season == season], left_on=["batter", "HitterSide"], right_on=["batter", "stand"], how="left", suffixes=("_base", "_raw"))
    print(season, "baseline rows", len(b), "| unmatched", m["PA_raw"].isna().sum(), "| PA mismatch", int((m["PA_base"] != m["PA_raw"]).sum()))
res.to_csv(REPO_ROOT / "analysis" / "kbb_traits.csv", index=False)
