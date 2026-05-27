# -*- coding: utf-8 -*-
"""
Created on Wed Feb 11 10:25:44 2026

@author: jaico

Example: How to use lineup context analysis with COMPREHENSIVE STATCAST METRICS
"""

from pathlib import Path
from statcast_research import df  # Your original PA-level data from CSVs
from lineup_context import calculate_all_conditional_stats
import pandas as pd

# Load full baselines (with all comprehensive Statcast metrics)
# Make sure you've run the updated analysis first to generate this!
baselines = pd.read_parquet("hitter_baselines_comprehensive.parquet")

# Calculate conditional stats for ALL players and save
# This shows each batter's performance when specific players batted before them
# NOW WITH 18 NEW STATCAST METRICS!
print("Calculating conditional lineup stats with comprehensive Statcast metrics...")
print("(This may take several minutes...)")

cache_dir = Path(__file__).parent.parent / "statcast_pitch_cache_2025"
print("Cache dir exists:", cache_dir.exists())

sample_files = list(cache_dir.glob("*.parquet"))[:10]
print("Sample cache files:")
for f in sample_files:
    print("  ", f.name)

# Check Mookie specifically
mookie_id = 605141
expected = cache_dir / f"{mookie_id}_2025-03-18_2025-09-28.parquet"
print("Expected Mookie file:", expected)
print("Mookie file exists:", expected.exists())

all_conditional = calculate_all_conditional_stats(
    df,
    baselines,  # Use comprehensive baselines with all Statcast metrics
    min_conditional_pas=30,  # Only include conditions with 30+ PAs
    pitch_cache_dir=str(cache_dir),
    start_date="2025-03-18",
    end_date="2025-09-28",
    include_bat_tracking=True  # Set to False for pre-2023 data
)

# Save for future use
all_conditional.to_parquet("conditional_lineup_stats_comprehensive_2025.parquet")
print(f"\n✅ Saved conditional stats for {len(all_conditional)} batter-condition pairs")
print(f"Total columns: {len(all_conditional.columns)}")

# Preview new columns
new_cols = [c for c in all_conditional.columns if any(x in c for x in ['SweetSpot', 'SwStr', 'Chase', 'Attack', 'Stance', 'Distance'])]
if new_cols:
    print(f"\n📊 New Statcast metrics added: {len(new_cols)} columns")
    print("Sample:", new_cols[:5])
