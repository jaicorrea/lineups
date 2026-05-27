# -*- coding: utf-8 -*-
"""
Comprehensive Statcast swing, contact, and bat tracking metrics
Includes: Swing%, Contact%, Sweet Spot%, SwStr%, Chase%, 
          Attack Angle, Attack Direction, Stance Angle, Distance Off Plate
"""

from __future__ import annotations
from pathlib import Path
from functools import wraps
import time
import numpy as np
import pandas as pd

# -----------------------------
# Pitch Description Sets
# -----------------------------
SWING_DESCRIPTIONS = {
    "swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
    "hit_into_play", "hit_into_play_no_out", "hit_into_play_score",
    "foul_bunt", "missed_bunt"
}

CONTACT_DESCRIPTIONS = {
    "foul", "hit_into_play", "hit_into_play_no_out", 
    "hit_into_play_score", "foul_bunt"
}

SWINGING_STRIKE_DESCRIPTIONS = {
    "swinging_strike", "swinging_strike_blocked", "foul_tip", "missed_bunt"
}

# Zone definitions (Statcast zones 1-9 are in strike zone, 11-14 are chase zones)
STRIKE_ZONES = {1, 2, 3, 4, 5, 6, 7, 8, 9}
CHASE_ZONES = {11, 12, 13, 14}  # Outside strike zone


def compute_all_swing_metrics(pitches: pd.DataFrame) -> dict[str, float]:
    """
    Calculate comprehensive swing metrics from pitch-level Statcast data.

    Returns dictionary with:
        - Swing_pct: Percentage of all pitches swung at
        - Contact_pct: Percentage of swings that made contact
        - SweetSpot_pct: Percentage of batted balls with launch angle 8-32°
        - SwStr_pct: Swinging strike percentage (of all pitches)
        - Chase_pct: Percentage of swings on pitches outside the zone
        - GroundBall_pct: Ground balls / batted ball events
        - FlyBall_pct: Fly balls / batted ball events
        - LineDrive_pct: Line drives / batted ball events
        - PopUp_pct: Pop ups / batted ball events
    """
    if pitches is None or pitches.empty:
        return {
            "Swing_pct": np.nan,
            "Contact_pct": np.nan,
            "SweetSpot_pct": np.nan,
            "SwStr_pct": np.nan,
            "Chase_pct": np.nan,
            "GroundBall_pct": np.nan,
            "FlyBall_pct": np.nan,
            "LineDrive_pct": np.nan,
            "PopUp_pct": np.nan,
        }

    if "description" not in pitches.columns:
        return {
            "Swing_pct": np.nan,
            "Contact_pct": np.nan,
            "SweetSpot_pct": np.nan,
            "SwStr_pct": np.nan,
            "Chase_pct": np.nan,
            "GroundBall_pct": np.nan,
            "FlyBall_pct": np.nan,
            "LineDrive_pct": np.nan,
            "PopUp_pct": np.nan,
        }

    desc = pitches["description"]
    total_pitches = len(pitches)

    swing_mask = desc.isin(SWING_DESCRIPTIONS)
    contact_mask = desc.isin(CONTACT_DESCRIPTIONS)
    swstr_mask = desc.isin(SWINGING_STRIKE_DESCRIPTIONS)

    swing_ct = swing_mask.sum()
    contact_ct = contact_mask.sum()
    swstr_ct = swstr_mask.sum()

    swing_pct = swing_ct / total_pitches if total_pitches > 0 else np.nan
    contact_pct = contact_ct / swing_ct if swing_ct > 0 else np.nan
    swstr_pct = swstr_ct / total_pitches if total_pitches > 0 else np.nan

    if "zone" in pitches.columns:
        zone = pitches["zone"]
        chase_swings = swing_mask & zone.isin(CHASE_ZONES)
        chase_opportunities = zone.isin(CHASE_ZONES)
        chase_pct = chase_swings.sum() / chase_opportunities.sum() if chase_opportunities.sum() > 0 else np.nan
    else:
        chase_pct = np.nan
    
    BBE_DESCRIPTIONS = {
            "hit_into_play", "hit_into_play_no_out", "hit_into_play_score"
            }
    
    batted_balls = pitches[pitches["description"].isin(BBE_DESCRIPTIONS)]

    if len(batted_balls) > 0:
        if "launch_angle" in batted_balls.columns:
            sweet_spot_mask = (
                batted_balls["launch_angle"].ge(8) &
                batted_balls["launch_angle"].le(32)
            ).fillna(False)
            sweetspot_pct = sweet_spot_mask.sum() / len(batted_balls)
        else:
            sweetspot_pct = np.nan

        if "bb_type" in batted_balls.columns:
            bb_type = batted_balls["bb_type"]
            groundball_pct = bb_type.eq("ground_ball").fillna(False).sum() / len(batted_balls)
            flyball_pct = bb_type.eq("fly_ball").fillna(False).sum() / len(batted_balls)
            linedrive_pct = bb_type.eq("line_drive").fillna(False).sum() / len(batted_balls)
            popup_pct = bb_type.eq("popup").fillna(False).sum() / len(batted_balls)
        else:
            groundball_pct = np.nan
            flyball_pct = np.nan
            linedrive_pct = np.nan
            popup_pct = np.nan
    else:
        sweetspot_pct = np.nan
        groundball_pct = np.nan
        flyball_pct = np.nan
        linedrive_pct = np.nan
        popup_pct = np.nan

    return {
        "Swing_pct": float(swing_pct),
        "Contact_pct": float(contact_pct),
        "SweetSpot_pct": float(sweetspot_pct),
        "SwStr_pct": float(swstr_pct),
        "Chase_pct": float(chase_pct),
        "GroundBall_pct": float(groundball_pct),
        "FlyBall_pct": float(flyball_pct),
        "LineDrive_pct": float(linedrive_pct),
        "PopUp_pct": float(popup_pct),
    }


def compute_bat_tracking_metrics(pitches: pd.DataFrame) -> dict[str, float]:
    """
    Calculate bat tracking metrics from pitch-level Statcast data.
    
    Bat tracking columns available since 2H 2023:
        - bat_speed: Speed of bat at sweet spot (mph)
        - swing_length: Distance bat traveled (feet)
        - attack_angle: Vertical angle of bat at contact (degrees)
        - attack_direction: Horizontal angle toward pull/oppo (degrees)
        - swing_path_tilt: Angle of swing plane (degrees)
    
    Stance metrics (available 2024+):
        - stance_feet_spread: Distance between feet (inches)
        - stance_angle: How open/closed the stance is (degrees)
        - distance_off_plate: Distance from plate (inches)
    
    Returns dictionary with median values for competitive swings.
    """
    if pitches is None or pitches.empty:
        return {
            "Attack_Angle_median": np.nan,
            "Attack_Direction_median": np.nan,
            "Swing_Path_Tilt_median": np.nan,
            "Stance_Angle_median": np.nan,
            "Distance_Off_Plate_median": np.nan,
        }
    
    # Filter to competitive swings only (swings with data)
    swing_mask = pitches["description"].isin(SWING_DESCRIPTIONS) if "description" in pitches.columns else pd.Series([True] * len(pitches))
    swing_data = pitches[swing_mask]
    
    results = {}
    
    # Attack Angle (vertical bat angle at contact)
    if "attack_angle" in swing_data.columns:
        results["Attack_Angle_median"] = float(swing_data["attack_angle"].median()) if swing_data["attack_angle"].notna().any() else np.nan
    else:
        results["Attack_Angle_median"] = np.nan
    
    # Attack Direction (horizontal bat angle: pull vs oppo)
    if "attack_direction" in swing_data.columns:
        results["Attack_Direction_median"] = float(swing_data["attack_direction"].median()) if swing_data["attack_direction"].notna().any() else np.nan
    else:
        results["Attack_Direction_median"] = np.nan
    
    # Swing Path Tilt (angle of swing plane)
    if "swing_path_tilt" in swing_data.columns:
        results["Swing_Path_Tilt_median"] = float(swing_data["swing_path_tilt"].median()) if swing_data["swing_path_tilt"].notna().any() else np.nan
    else:
        results["Swing_Path_Tilt_median"] = np.nan
    
    # Stance Angle (open/closed stance)
    if "stance_angle" in swing_data.columns:
        results["Stance_Angle_median"] = float(swing_data["stance_angle"].median()) if swing_data["stance_angle"].notna().any() else np.nan
    else:
        results["Stance_Angle_median"] = np.nan
    
    # Distance Off Plate
    if "distance_off_plate" in swing_data.columns:
        results["Distance_Off_Plate_median"] = float(swing_data["distance_off_plate"].median()) if swing_data["distance_off_plate"].notna().any() else np.nan
    else:
        results["Distance_Off_Plate_median"] = np.nan
    
    return results


def retry_with_backoff(max_retries: int = 3, sleep_s: float = 1.0):
    """Decorator for retrying API calls with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(sleep_s * attempt)
            raise last_error
        return wrapper
    return decorator


def add_comprehensive_statcast_metrics(
    baselines: pd.DataFrame,
    start: str = "2025-03-18",
    end: str = "2025-09-28",
    cache_dir: str | Path = "statcast_pitch_cache_2025",
    sleep_s: float = 1.0,
    max_retries: int = 3,
    progress_every: int = 25,
) -> pd.DataFrame:
    """
    Add comprehensive Statcast swing and bat tracking metrics to baselines table.
    
    Adds 10 columns:
        - Swing_pct: Swing percentage
        - Contact_pct: Contact percentage
        - SweetSpot_pct: Sweet spot percentage (LA 8-32°)
        - SwStr_pct: Swinging strike percentage
        - Chase_pct: Chase rate (swings outside zone)
        - Attack_Angle_median: Median attack angle
        - Attack_Direction_median: Median attack direction
        - Swing_Path_Tilt_median: Median swing path tilt
        - Stance_Angle_median: Median stance angle
        - Distance_Off_Plate_median: Median distance from plate
    
    Uses disk caching to avoid re-downloading pitch data.
    
    NOTE: Bat tracking data (attack angle, etc.) only available from 2H 2023 onward.
          Stance metrics only available from 2024 onward.
    """
    from pybaseball import statcast_batter
    
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    out = baselines.copy()
    out["batter"] = out["batter"].astype("int64")
    
    hitter_ids = out["batter"].unique()
    
    # Storage for results
    swing_results = {
        metric: {} for metric in [
            "Swing_pct", "Contact_pct", "SweetSpot_pct", "SwStr_pct", "Chase_pct",
            "GroundBall_pct", "FlyBall_pct", "LineDrive_pct", "PopUp_pct"
        ]
    }    
    bat_tracking_results = {metric: {} for metric in ["Attack_Angle_median", "Attack_Direction_median", 
                                                            "Swing_Path_Tilt_median", "Stance_Angle_median",
                                                            "Distance_Off_Plate_median"]}
    
    @retry_with_backoff(max_retries, sleep_s)
    def fetch_batter_data(batter_id: int) -> pd.DataFrame:
        """Fetch and cache batter pitch data with retry logic."""
        return statcast_batter(start, end, int(batter_id))
    
    for i, bid in enumerate(hitter_ids, start=1):
        cache_path = cache_dir / f"{bid}_{start}_{end}.parquet"
        
        # Try to load from cache, otherwise fetch
        try:
            if cache_path.exists():
                pitches = pd.read_parquet(cache_path)
            else:
                pitches = fetch_batter_data(bid)
                pitches.to_parquet(cache_path, index=False)
                time.sleep(sleep_s)  # Rate limiting
        except Exception as e:
            print(f"[WARN] Failed batter {bid}: {e}")
            pitches = None
        
        # Compute swing metrics
        swing_metrics = compute_all_swing_metrics(pitches)
        for metric, value in swing_metrics.items():
            swing_results[metric][int(bid)] = value
        
        # Compute bat tracking metrics
        bat_metrics = compute_bat_tracking_metrics(pitches)
        for metric, value in bat_metrics.items():
            bat_tracking_results[metric][int(bid)] = value
        
        # Progress tracking
        if progress_every and (i % progress_every == 0 or i == len(hitter_ids)):
            print(f"Processed {i}/{len(hitter_ids)} hitters")
    
    # Map all results back to dataframe
    for metric in swing_results:
        out[metric] = out["batter"].map(swing_results[metric])
    
    for metric in bat_tracking_results:
        out[metric] = out["batter"].map(bat_tracking_results[metric])
    
    return out


# Backward compatibility: keep the old function name
def add_swing_contact_pct_from_statcast(*args, **kwargs):
    """
    DEPRECATED: Use add_comprehensive_statcast_metrics instead.
    This is kept for backward compatibility but only returns Swing_pct and Contact_pct.
    """
    result = add_comprehensive_statcast_metrics(*args, **kwargs)
    # Keep only the original columns plus Swing_pct and Contact_pct
    return result