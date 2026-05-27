# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 15:06:51 2026

@author: jaico
"""
# run this so you don't have to keep running the data

from pathlib import Path
import pandas as pd

repo_root = Path(__file__).parent.parent

# Load and export baselines to CSV
baselines = pd.read_parquet("hitter_baselines_full_2025.parquet")
baselines.to_csv(str(repo_root / "hitter_baselines_full_2025.csv"), index=False)
print("Baselines exported to CSV")

# Load conditional lineup stats
conditional_stats = pd.read_parquet("conditional_lineup_stats_comprehensive_2025.parquet")

# Example: Check Shohei Ohtani's stats when different batters hit before him
ohtani_stats = conditional_stats[conditional_stats['focal_batter_name'] == 'Ohtani, Shohei']
print("\nShohei Ohtani's performance by who batted before him:")
print(ohtani_stats[['conditional_batter_name', 'num_PAs', 'focal_BA', 'focal_OBP', 'focal_SLG', 'focal_delta_run_exp_PA']])

# Example: Check who performs best when Ohtani bats before them
after_ohtani = conditional_stats[conditional_stats['conditional_batter_name'] == 'Ohtani, Shohei']
print("\nBatters who hit after Ohtani:")
print(after_ohtani.nlargest(5, 'focal_OBP')[['focal_batter_name', 'num_PAs', 'focal_BA', 'focal_OBP', 'focal_SLG']])

# Export conditional stats to CSV as well
conditional_stats.to_csv(str(repo_root / "conditional_lineup_stats_2025.csv"), index=False)
print("\nConditional stats exported to CSV")
