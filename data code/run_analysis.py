# -*- coding: utf-8 -*-
"""
Created on Thu Feb  5 15:35:48 2026

@author: jaico
"""

from pathlib import Path
from statcast_research import df
from avghitter import hitter_baselines_from_pa_df
from swing_and_battracking_metrics import add_comprehensive_statcast_metrics

# Generate baseline stats from PA-level data
baselines = hitter_baselines_from_pa_df(df, min_pa=50)

# Add comprehensive swing and bat tracking metrics
# This adds 10 new columns:
#   - Swing_pct, Contact_pct, SweetSpot_pct, SwStr_pct, Chase_pct
#   - Attack_Angle_median, Attack_Direction_median, Swing_Path_Tilt_median
#   - Stance_Angle_median, Distance_Off_Plate_median
baselines = add_comprehensive_statcast_metrics(
    baselines,
    start="2025-03-18",
    end="2025-09-28",
    cache_dir=Path(__file__).parent.parent / "statcast_pitch_cache_2025",
    progress_every=25
)

print(baselines.head())
print(f"\nTotal columns: {len(baselines.columns)}")
print(f"Columns: {list(baselines.columns)}")

# Optionally save to parquet for future use
baselines.to_parquet("hitter_baselines_comprehensive.parquet", index=False)
print("\nSaved to: hitter_baselines_comprehensive.parquet")
