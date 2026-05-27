# -*- coding: utf-8 -*-
"""
Created on Thu Feb  5 14:50:57 2026

@author: jaico
"""

import numpy as np
import pandas as pd

# -----------------------
# 1) Barrel flag (approx from launch_speed + launch_angle)
# -----------------------
def approx_is_barrel(ev_mph: float, la_deg: float) -> bool:
    """
    Approximation based on MLB Statcast's published barrel window.
    Linear expansion from 98-100 mph (1 deg/mph), then faster 100+ mph (2 deg/mph).
    """
    if pd.isna(ev_mph) or pd.isna(la_deg) or ev_mph < 98:
        return False
    if ev_mph >= 116:
        return 8 <= la_deg <= 50

    if ev_mph < 101:
        lo = 26 - (ev_mph - 98)      # shrinks 1 per mph
        hi = 30 + (ev_mph - 98)      # grows 1 per mph
    else:
        extra = int(np.floor(ev_mph - 100))
        lo = max(24 - 2 * extra, 8)  # shrinks 2 per mph
        hi = min(33 + 2 * extra, 50) # grows 2 per mph

    return lo <= la_deg <= hi

def mode_or_nan(s: pd.Series):
    s = s.dropna()
    return s.mode().iloc[0] if not s.empty else np.nan

# -----------------------
# 2) Per-hitter baselines from your PA-level df
# -----------------------
def hitter_baselines_from_pa_df(df: pd.DataFrame, min_pa: int | None = None) -> pd.DataFrame:
    d = df.copy()
    # One player_name per batter (Statcast format: "Last, First")
    name_df = (
        d[["batter", "player_name"]]
        .dropna()
        .drop_duplicates("batter")
        )

    # Ensure numeric where needed
    for c in ["pitch_number", "launch_speed", "launch_angle", "plate_x", "plate_z", "delta_run_exp"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")

    # Each row is already one PA
    d["PA"] = 1

    # --- Events mapping for BA/OBP/SLG (matches your ath.csv event labels) ---
    hit_tb = {"single": 1, "double": 2, "triple": 3, "home_run": 4}
    d["TB"] = d["events"].map(hit_tb).fillna(0).astype(int)
    d["H"]  = (d["TB"] > 0).astype(int)

    d["BB"]  = d["events"].isin(["walk", "intent_walk"]).astype(int)
    d["HBP"] = (d["events"] == "hit_by_pitch").astype(int)

    # You said: hits / (pa - bb - hbp - sacrifice)
    # In your data you have sac_fly and sac_bunt
    d["SAC"] = d["events"].isin(["sac_fly", "sac_bunt"]).astype(int)

    # Catcher's interference is not an AB; treat like a non-AB event
    d["CI"] = (d["events"] == "catcher_interf").astype(int)

    d["AB"] = (d["PA"] - d["BB"] - d["HBP"] - d["SAC"] - d["CI"]).clip(lower=0)

    # Barrel flag (approx)
    d["is_barrel"] = d.apply(lambda r: int(approx_is_barrel(r["launch_speed"], r["launch_angle"])), axis=1)

    # Aggregate per hitter AND batting side (for switch hitters)
    out = (
        d.groupby(["batter", "stand"], as_index=False)
         .agg(
             PA=("PA", "sum"),
             Barrels=("is_barrel", "sum"),
             pitches_sum=("pitch_number", "sum"),
             H=("H", "sum"),
             TB=("TB", "sum"),
             AB=("AB", "sum"),
             BB=("BB", "sum"),
             HBP=("HBP", "sum"),
             SAC=("SAC", "sum"),
             SF=("events", lambda s: int((s == "sac_fly").sum())),  # for OBP denominator
             delta_run_exp_sum=("delta_run_exp", "sum"),
         )
    )
    
    # Rename 'stand' to 'HitterSide' for clarity
    out = out.rename(columns={'stand': 'HitterSide'})
    
    out = out.merge(name_df, on="batter", how="left")
    
    # Barrel / PA
    out["Barrel_PA"] = np.where(out["PA"] > 0, out["Barrels"] / out["PA"], np.nan)

    # Pitches per PA (your formula)
    out["Pitch_PA"] = np.where(out["PA"] > 0, out["pitches_sum"] / out["PA"], np.nan)

    # Delta run expectancy per PA
    out["delta_run_exp_PA"] = np.where(out["PA"] > 0, out["delta_run_exp_sum"] / out["PA"], np.nan)

    # BA
    out["BA"] = np.where(out["AB"] > 0, out["H"] / out["AB"], np.nan)

    # OBP (standard): (H + BB + HBP) / (AB + BB + HBP + SF)
    denom_obp = out["AB"] + out["BB"] + out["HBP"] + out["SF"]
    out["OBP"] = np.where(denom_obp > 0, (out["H"] + out["BB"] + out["HBP"]) / denom_obp, np.nan)

    # SLG
    out["SLG"] = np.where(out["AB"] > 0, out["TB"] / out["AB"], np.nan)

    # Nitro Zone you requested = median plate_x/z for barreled PAs
    barrel_meds = (
        d.loc[d["is_barrel"] == 1]
         .groupby("batter", as_index=False)
         .agg(
             Nitro_med_plate_x=("plate_x", "median"),
             Nitro_med_plate_z=("plate_z", "median"),
         )
    )
    out = out.merge(barrel_meds, on="batter", how="left")

    # Optional sample-size filter
    if min_pa is not None:
        out = out.query("PA >= @min_pa").reset_index(drop=True)

    out["Nitro_med_xy"] = list(zip(out["Nitro_med_plate_x"], out["Nitro_med_plate_z"]))
    out = out.drop(columns=["Nitro_med_plate_x", "Nitro_med_plate_z"])

    # Keep clean columns
    out = out[[
    "batter",
    "player_name",
    "HitterSide",
    "PA",
    "Barrel_PA",
    "Pitch_PA",
    "BA", "OBP", "SLG",
    "delta_run_exp_PA",
    "Nitro_med_xy"
    ]]
    return out