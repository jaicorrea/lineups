# -*- coding: utf-8 -*-
"""
Created on Wed Feb 11 13:49:27 2026

@author: jaico
"""

from pathlib import Path
import pandas as pd

repo_root = Path(__file__).parent.parent

baselines = pd.read_parquet("hitter_baselines_full_2025.parquet")
all_conditional = pd.read_parquet("conditional_lineup_stats_2025.parquet")

# 1) Make sure IDs match type
all_conditional["focal_batter_id"] = all_conditional["focal_batter_id"].astype("int64")
all_conditional["conditional_batter_id"] = all_conditional["conditional_batter_id"].astype("int64")
baselines["batter"] = baselines["batter"].astype("int64")

# 2) Add season-long stats for the CONDITIONAL batter
# all_conditional already has ALL focal player stats (both conditional and season)
# We only need to add the conditional batter's season stats

conditional_season = baselines[[
    "batter", "HitterSide", "PA", "Barrel_PA", "Pitch_PA",
    "BA", "OBP", "SLG", "delta_run_exp_PA", "Swing_pct", "Contact_pct", "Nitro_med_xy"
]].rename(columns={
    "batter": "conditional_batter_id",
    "HitterSide": "conditional_HitterSide",
    "PA": "conditional_season_PA",
    "Barrel_PA": "conditional_season_Barrel_PA",
    "Pitch_PA": "conditional_season_Pitch_PA",
    "BA": "conditional_season_BA",
    "OBP": "conditional_season_OBP",
    "SLG": "conditional_season_SLG",
    "delta_run_exp_PA": "conditional_season_delta_run_exp_PA",
    "Swing_pct": "conditional_season_Swing_pct",
    "Contact_pct": "conditional_season_Contact_pct",
    "Nitro_med_xy": "conditional_season_Nitro_med_xy"
})

# 3) Merge conditional season stats onto all_conditional
out = all_conditional.merge(conditional_season, on=["conditional_batter_id", "conditional_HitterSide"], how="left")

# 4) Reorder columns for clean organization: all focal stats first, then all conditional stats
focal_cols = [col for col in out.columns if col.startswith('focal_')]
conditional_cols = [col for col in out.columns if col.startswith('conditional_')]
other_cols = [col for col in out.columns if not col.startswith('focal_') and not col.startswith('conditional_')]

# Arrange as: IDs/sides, num_PAs, focal stats, conditional stats
final_order = other_cols[:7] + focal_cols + conditional_cols  # First 7 are IDs, sides, and num_PAs
out = out[final_order]

# Export to CSV
out.to_csv(str(repo_root / "conditional_stats_with_baselines.csv"), index=False)
print(f"\n✅ Exported {len(out)} rows to repo root: conditional_stats_with_baselines.csv")
print(f"\nColumns: {len(out.columns)}")
print(f"Sample columns: {out.columns[:10].tolist()}")
