# -*- coding: utf-8 -*-
"""
Created on Wed Feb 11 13:49:27 2026

@author: jaico
"""

from pathlib import Path
import pandas as pd

repo_root = Path(__file__).parent.parent

all_conditional = pd.read_parquet("conditional_lineup_stats_comprehensive_2025.parquet")

# 1) Make sure IDs match type
all_conditional["focal_batter_id"] = all_conditional["focal_batter_id"].astype("int64")
all_conditional["conditional_batter_id"] = all_conditional["conditional_batter_id"].astype("int64")

# NOTE: the current lineup_context.py pipeline already merges the conditional
# batter's season stats (including conditional_season_Nitro_med_xy) into
# all_conditional directly, so no separate merge with baselines is needed here.
out = all_conditional

# 3b) Unpack Nitro_med_xy (plate_x, plate_z) tuples into plain numeric columns.
# Stored as tuples/arrays in the parquet pipeline (None-filled when a batter has
# no barrels to compute a median location from); CSV export would otherwise
# stringify them (e.g. "[0.135 2.615]"), which isn't usable in a regression.
def _nitro_component(value, index):
    if value is None:
        return pd.NA
    try:
        component = value[index]
    except (TypeError, IndexError):
        return pd.NA
    return pd.NA if component is None else float(component)

for prefix in ["focal_season", "conditional_season", "focal", "conditional"]:
    col = f"{prefix}_Nitro_med_xy"
    if col in out.columns:
        out[f"{prefix}_nitro_x"] = out[col].apply(lambda v: _nitro_component(v, 0))
        out[f"{prefix}_nitro_z"] = out[col].apply(lambda v: _nitro_component(v, 1))

# Euclidean distance between the focal and conditional hitters' season-long
# barrel "nitro zone" locations -- how far apart their hot zones sit in the
# strike zone, combining both the horizontal (x) and vertical (z) axes.
out["nitro_dist"] = (
    (out["focal_season_nitro_x"] - out["conditional_season_nitro_x"]) ** 2
    + (out["focal_season_nitro_z"] - out["conditional_season_nitro_z"]) ** 2
) ** 0.5

# 4) Reorder columns for clean organization: all focal stats first, then all conditional stats
focal_cols = [col for col in out.columns if col.startswith('focal_')]
conditional_cols = [col for col in out.columns if col.startswith('conditional_')]
other_cols = [col for col in out.columns if not col.startswith('focal_') and not col.startswith('conditional_')]

# Arrange as: non-prefixed columns (num_PAs, nitro_dist) first, then focal
# stats, then conditional stats. All ID/side columns already carry a
# focal_/conditional_ prefix, so they're picked up by those groups directly.
final_order = other_cols + focal_cols + conditional_cols
out = out[final_order]

# Export to CSV
out.to_csv(str(repo_root / "conditional_stats_with_baselines.csv"), index=False)
print(f"\nExported {len(out)} rows to repo root: conditional_stats_with_baselines.csv")
print(f"\nColumns: {len(out.columns)}")
print(f"Sample columns: {out.columns[:10].tolist()}")
