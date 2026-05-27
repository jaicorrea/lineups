# -*- coding: utf-8 -*-
"""
Created for lineup context analysis

Calculate average stats for batters hitting before/after each player
NOW WITH COMPREHENSIVE STATCAST METRICS
"""

import numpy as np
import pandas as pd
from pathlib import Path


def get_actual_before_after_batters(pa_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each PA, identify who actually batted immediately before and after.
    
    Parameters:
    -----------
    pa_df : DataFrame
        At-bat level data with: game_pk (or game_date+team), at_bat_number, batter
        
    Returns:
    --------
    DataFrame with additional columns:
        - batter_before: player ID who batted immediately before
        - batter_after: player ID who batted immediately after
    """
    d = pa_df.copy()
    
    # Identify unique games
    if 'game_pk' in d.columns:
        game_id = 'game_pk'
    else:
        d['game_id'] = d['game_date'].astype(str) + '_' + d['team'].astype(str)
        game_id = 'game_id'
    
    # Sort by game and at-bat order
    d = d.sort_values([game_id, 'at_bat_number']).reset_index(drop=True)
    
    # Shift within each game to get before/after batters AND their batting sides
    d['batter_before'] = d.groupby(game_id)['batter'].shift(1)
    d['batter_after'] = d.groupby(game_id)['batter'].shift(-1)
    d['stand_before'] = d.groupby(game_id)['stand'].shift(1)  # NEW: batting side of previous batter
    d['stand_after'] = d.groupby(game_id)['stand'].shift(-1)
    
    # Clean up temp column if created
    if game_id == 'game_id':
        d = d.drop(columns=['game_id'])
    
    return d


def calculate_conditional_stats(
    pa_df: pd.DataFrame,
    baselines: pd.DataFrame,
    focal_batter_name: str,
    condition: str = 'before'  # 'before' or 'after'
) -> pd.DataFrame:
    """
    Calculate focal batter's stats grouped by who batted before/after them.
    
    Parameters:
    -----------
    pa_df : DataFrame
        At-bat level data with batter_before and batter_after columns
    baselines : DataFrame
        Player stats lookup table with batter, player_name
    focal_batter_name : str
        Name of player to analyze (e.g., "Betts, Mookie")
    condition : str
        'before' = group by who batted before focal player
        'after' = group by who batted after focal player
        
    Returns:
    --------
    DataFrame with one row per conditional batter showing focal player's stats
    in games when that person batted before/after them.
    
    Columns:
        - conditional_batter_id
        - conditional_batter_name
        - num_PAs (how many PAs with this condition)
        - focal_Barrel_PA, focal_Pitch_PA, focal_BA, focal_OBP, focal_SLG, focal_Nitro_med_xy
        
    Note: Swing_pct and Contact_pct require pitch-level data and cannot be calculated
    from at-bat level data.
    """
    # Add before/after info if not already present
    if 'batter_before' not in pa_df.columns or 'batter_after' not in pa_df.columns:
        pa_df = get_actual_before_after_batters(pa_df)
    
    # Get focal batter ID
    focal_row = baselines[baselines['player_name'] == focal_batter_name]
    if focal_row.empty:
        print(f"Player '{focal_batter_name}' not found in baselines")
        return pd.DataFrame()
    
    focal_batter_id = focal_row['batter'].iloc[0]
    
    # Filter to focal batter's PAs only
    focal_pas = pa_df[pa_df['batter'] == focal_batter_id].copy()
    
    if focal_pas.empty:
        print(f"No PAs found for {focal_batter_name}")
        return pd.DataFrame()
    
    # Choose the conditioning column
    condition_col = 'batter_before' if condition == 'before' else 'batter_after'
    
    # Drop rows where condition is missing (first/last PA of games)
    focal_pas = focal_pas.dropna(subset=[condition_col])
    
    # Calculate stats for the focal batter, grouped by the conditional batter
    # We need to recalculate BA, OBP, SLG from events
    
    # Add outcome flags
    hit_tb = {"single": 1, "double": 2, "triple": 3, "home_run": 4}
    focal_pas["TB"] = focal_pas["events"].map(hit_tb).fillna(0).astype(int)
    focal_pas["H"] = (focal_pas["TB"] > 0).astype(int)
    focal_pas["BB"] = focal_pas["events"].isin(["walk", "intent_walk"]).astype(int)
    focal_pas["HBP"] = (focal_pas["events"] == "hit_by_pitch").astype(int)
    focal_pas["SAC"] = focal_pas["events"].isin(["sac_fly", "sac_bunt"]).astype(int)
    focal_pas["CI"] = (focal_pas["events"] == "catcher_interf").astype(int)
    focal_pas["SF"] = (focal_pas["events"] == "sac_fly").astype(int)
    focal_pas["PA"] = 1
    focal_pas["AB"] = (focal_pas["PA"] - focal_pas["BB"] - focal_pas["HBP"] - 
                       focal_pas["SAC"] - focal_pas["CI"]).clip(lower=0)
    
    # Add barrel and pitch count
    from avghitter import approx_is_barrel
    focal_pas["is_barrel"] = focal_pas.apply(
        lambda r: int(approx_is_barrel(r.get("launch_speed"), r.get("launch_angle"))), 
        axis=1
    )
    
    # Ensure numeric
    for c in ["pitch_number", "launch_speed", "launch_angle", "plate_x", "plate_z", "delta_run_exp"]:
        if c in focal_pas.columns:
            focal_pas[c] = pd.to_numeric(focal_pas[c], errors="coerce")
    
    # Group by conditional batter
    grouped = (
        focal_pas.groupby(condition_col)
        .agg(
            num_PAs=("PA", "sum"),
            H=("H", "sum"),
            TB=("TB", "sum"),
            AB=("AB", "sum"),
            BB=("BB", "sum"),
            HBP=("HBP", "sum"),
            SF=("SF", "sum"),
            Barrels=("is_barrel", "sum"),
            pitches_sum=("pitch_number", "sum"),
            delta_run_exp_sum=("delta_run_exp", "sum"),
        )
        .reset_index()
        .rename(columns={condition_col: 'conditional_batter_id'})
    )
    
    # Calculate Nitro zone (median plate location for barrels)
    def calc_nitro_zone(group):
        barrels = group[group['is_barrel'] == 1]
        if len(barrels) > 0 and 'plate_x' in group.columns and 'plate_z' in group.columns:
            med_x = barrels['plate_x'].median()
            med_z = barrels['plate_z'].median()
            return pd.Series({'nitro_x': med_x, 'nitro_z': med_z})
        else:
            return pd.Series({'nitro_x': np.nan, 'nitro_z': np.nan})
    
    nitro_stats = focal_pas.groupby(condition_col).apply(calc_nitro_zone).reset_index()
    nitro_stats = nitro_stats.rename(columns={condition_col: 'conditional_batter_id'})
    grouped = grouped.merge(nitro_stats, on='conditional_batter_id', how='left')
    
    # Calculate rate stats (matching baselines)
    grouped['focal_BA'] = np.where(grouped['AB'] > 0, grouped['H'] / grouped['AB'], np.nan)
    grouped['focal_SLG'] = np.where(grouped['AB'] > 0, grouped['TB'] / grouped['AB'], np.nan)
    
    denom_obp = grouped['AB'] + grouped['BB'] + grouped['HBP'] + grouped['SF']
    grouped['focal_OBP'] = np.where(
        denom_obp > 0, 
        (grouped['H'] + grouped['BB'] + grouped['HBP']) / denom_obp, 
        np.nan
    )
    
    grouped['focal_Barrel_PA'] = np.where(
        grouped['num_PAs'] > 0, 
        grouped['Barrels'] / grouped['num_PAs'], 
        np.nan
    )
    
    grouped['focal_Pitch_PA'] = np.where(
        grouped['num_PAs'] > 0, 
        grouped['pitches_sum'] / grouped['num_PAs'], 
        np.nan
    )
    
    grouped['focal_delta_run_exp_PA'] = np.where(
        grouped['num_PAs'] > 0,
        grouped['delta_run_exp_sum'] / grouped['num_PAs'],
        np.nan
    )
    
    # Create Nitro_med_xy tuple
    grouped['focal_Nitro_med_xy'] = list(zip(grouped['nitro_x'], grouped['nitro_z']))
    grouped = grouped.drop(columns=['nitro_x', 'nitro_z'])
    
    # Add conditional batter names
    conditional_names = baselines[['batter', 'player_name']].drop_duplicates('batter').rename(
        columns={'batter': 'conditional_batter_id', 'player_name': 'conditional_batter_name'}
    )
    grouped = grouped.merge(conditional_names, on='conditional_batter_id', how='left')
    
    # Clean up columns
    grouped = grouped.drop(columns=['H', 'TB', 'AB', 'BB', 'HBP', 'SF', 'Barrels', 'pitches_sum', 'delta_run_exp_sum'])
    
    return grouped


def compute_swing_contact_pct(pitches: pd.DataFrame) -> tuple[float, float]:
    """Calculate Swing% and Contact% from pitch-level data."""
    # Import from the comprehensive metrics module
    from swing_and_battracking_metrics import compute_all_swing_metrics
    
    metrics = compute_all_swing_metrics(pitches)
    return metrics['Swing_pct'], metrics['Contact_pct']


def compute_comprehensive_swing_metrics(pitches: pd.DataFrame) -> dict:
    """
    Calculate all 10 Statcast metrics from pitch-level data.
    
    Returns dict with: Swing_pct, Contact_pct, SweetSpot_pct, SwStr_pct, Chase_pct,
                       Attack_Angle_median, Attack_Direction_median, Swing_Path_Tilt_median,
                       Stance_Angle_median, Distance_Off_Plate_median
    """
    from swing_and_battracking_metrics import compute_all_swing_metrics, compute_bat_tracking_metrics
    
    swing_metrics = compute_all_swing_metrics(pitches)
    bat_tracking = compute_bat_tracking_metrics(pitches)
    
    # Combine all metrics
    return {**swing_metrics, **bat_tracking}


def calculate_all_conditional_stats(
    pa_df: pd.DataFrame,
    baselines: pd.DataFrame,
    min_conditional_pas: int = 30,
    pitch_cache_dir: str = "statcast_pitch_cache_2025",
    start_date: str = "2025-03-18",
    end_date: str = "2025-09-28",
    include_bat_tracking: bool = True  # NEW: option to include bat tracking metrics
) -> pd.DataFrame:
    """
    Calculate conditional stats for ALL batters (grouped by who batted before them).
    NOW WITH COMPREHENSIVE STATCAST METRICS!
    
    Parameters:
    -----------
    pa_df : DataFrame
        PA-level data with game_pk, at_bat_number, batter, stand
    baselines : DataFrame
        Season-long baselines with all metrics (including Swing_pct, Contact_pct, etc.)
    min_conditional_pas : int
        Minimum PAs required for a condition to be included
    pitch_cache_dir : str
        Directory with cached pitch-level data
    start_date, end_date : str
        Date range for filtering pitch data
    include_bat_tracking : bool
        If True, adds bat tracking metrics (Attack Angle, Stance Angle, etc.)
        Set to False if analyzing pre-2023 data (bat tracking not available)
        
    Returns:
    --------
    DataFrame with conditional stats for all focal/conditional batter pairs.
    
    NEW COLUMNS ADDED (if include_bat_tracking=True):
        Focal batter (conditional):
            - focal_SweetSpot_pct
            - focal_SwStr_pct  
            - focal_Chase_pct
            - focal_Attack_Angle_median
            - focal_Attack_Direction_median
            - focal_Swing_Path_Tilt_median
            - focal_Stance_Angle_median
            - focal_Distance_Off_Plate_median
            
        Focal batter (season):
            - focal_season_SweetSpot_pct
            - focal_season_SwStr_pct
            - focal_season_Chase_pct
            - focal_season_Attack_Angle_median
            - focal_season_Attack_Direction_median
            - focal_season_Swing_Path_Tilt_median
            - focal_season_Stance_Angle_median
            - focal_season_Distance_Off_Plate_median
    """
    d = get_actual_before_after_batters(pa_df)
    
    # Add stand_before column if not present
    if 'stand_before' not in d.columns:
        if 'game_pk' in d.columns:
            game_id = 'game_pk'
        else:
            d['temp_game_id'] = d['game_date'].astype(str) + '_' + d['team'].astype(str)
            game_id = 'temp_game_id'
        d = d.sort_values([game_id, 'at_bat_number']).reset_index(drop=True)
        d['stand_before'] = d.groupby(game_id)['stand'].shift(1)
        if game_id == 'temp_game_id':
            d = d.drop(columns=['temp_game_id'])
    
    # Filter out first PAs (no batter before)
    d = d.dropna(subset=['batter_before', 'stand_before'])
    
    # Calculate outcome flags
    hit_tb = {"single": 1, "double": 2, "triple": 3, "home_run": 4}
    d["TB"] = d["events"].map(hit_tb).fillna(0).astype(int)
    d["H"] = (d["TB"] > 0).astype(int)
    d["BB"] = d["events"].isin(["walk", "intent_walk"]).astype(int)
    d["HBP"] = (d["events"] == "hit_by_pitch").astype(int)
    d["SAC"] = d["events"].isin(["sac_fly", "sac_bunt"]).astype(int)
    d["CI"] = (d["events"] == "catcher_interf").astype(int)
    d["SF"] = (d["events"] == "sac_fly").astype(int)
    d["PA"] = 1
    d["AB"] = (d["PA"] - d["BB"] - d["HBP"] - d["SAC"] - d["CI"]).clip(lower=0)
    
    # Barrel detection
    from avghitter import approx_is_barrel
    for c in ["launch_speed", "launch_angle", "pitch_number", "plate_x", "plate_z", "delta_run_exp"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    
    d["is_barrel"] = d.apply(
        lambda r: int(approx_is_barrel(r.get("launch_speed"), r.get("launch_angle"))), 
        axis=1
    )
    
    # Group by focal batter, conditional batter, AND both batting sides
    grouped = (
        d.groupby(['batter', 'stand', 'batter_before', 'stand_before'])
        .agg(
            num_PAs=("PA", "sum"),
            # Focal batter stats
            H=("H", "sum"),
            TB=("TB", "sum"),
            AB=("AB", "sum"),
            BB=("BB", "sum"),
            HBP=("HBP", "sum"),
            SF=("SF", "sum"),
            Barrels=("is_barrel", "sum"),
            pitches_sum=("pitch_number", "sum"),
            delta_run_exp_sum=("delta_run_exp", "sum"),
        )
        .reset_index()
        .rename(columns={
            'batter': 'focal_batter_id',
            'stand': 'focal_HitterSide',
            'batter_before': 'conditional_batter_id',
            'stand_before': 'conditional_HitterSide'
        })
    )
    
    # Filter by minimum PAs
    grouped = grouped[grouped['num_PAs'] >= min_conditional_pas].reset_index(drop=True)
    
    # Calculate Nitro zone
    def calc_nitro_zone(group):
        barrels = group[group['is_barrel'] == 1]
        if len(barrels) > 0 and 'plate_x' in group.columns and 'plate_z' in group.columns:
            med_x = barrels['plate_x'].median()
            med_z = barrels['plate_z'].median()
            return pd.Series({'nitro_x': med_x, 'nitro_z': med_z})
        else:
            return pd.Series({'nitro_x': np.nan, 'nitro_z': np.nan})
    
    nitro_stats = d.groupby(['batter', 'stand', 'batter_before', 'stand_before']).apply(calc_nitro_zone).reset_index()
    nitro_stats = nitro_stats.rename(columns={
        'batter': 'focal_batter_id',
        'stand': 'focal_HitterSide',
        'batter_before': 'conditional_batter_id',
        'stand_before': 'conditional_HitterSide'
    })
    results = grouped.merge(nitro_stats, on=['focal_batter_id', 'focal_HitterSide', 
                                              'conditional_batter_id', 'conditional_HitterSide'], how='left')
    
    # Calculate focal batter rate stats
    results['focal_BA'] = np.where(results['AB'] > 0, results['H'] / results['AB'], np.nan)
    results['focal_SLG'] = np.where(results['AB'] > 0, results['TB'] / results['AB'], np.nan)
    
    denom_obp = results['AB'] + results['BB'] + results['HBP'] + results['SF']
    results['focal_OBP'] = np.where(denom_obp > 0, (results['H'] + results['BB'] + results['HBP']) / denom_obp, np.nan)
    
    results['focal_Barrel_PA'] = np.where(results['num_PAs'] > 0, results['Barrels'] / results['num_PAs'], np.nan)
    results['focal_Pitch_PA'] = np.where(results['num_PAs'] > 0, results['pitches_sum'] / results['num_PAs'], np.nan)
    results['focal_delta_run_exp_PA'] = np.where(results['num_PAs'] > 0, results['delta_run_exp_sum'] / results['num_PAs'], np.nan)
    
    # Calculate conditional batter stats (their actual performance in those same PAs)
    conditional_grouped = (
        d.groupby(['batter', 'stand', 'batter_before', 'stand_before'])
        .agg(
            H_before=("H", lambda x: x.shift(1).sum()),  # Stats from previous PA
            TB_before=("TB", lambda x: x.shift(1).sum()),
            AB_before=("AB", lambda x: x.shift(1).sum()),
            BB_before=("BB", lambda x: x.shift(1).sum()),
            HBP_before=("HBP", lambda x: x.shift(1).sum()),
            SF_before=("SF", lambda x: x.shift(1).sum()),
            Barrels_before=("is_barrel", lambda x: x.shift(1).sum()),
            pitches_sum_before=("pitch_number", lambda x: x.shift(1).sum()),
            delta_run_exp_sum_before=("delta_run_exp", lambda x: x.shift(1).sum()),
        )
        .reset_index()
        .rename(columns={
            'batter': 'focal_batter_id',
            'stand': 'focal_HitterSide',
            'batter_before': 'conditional_batter_id',
            'stand_before': 'conditional_HitterSide'
        })
    )
    
    results = results.merge(conditional_grouped, 
                           on=['focal_batter_id', 'focal_HitterSide', 'conditional_batter_id', 'conditional_HitterSide'], 
                           how='left')
    
    results['conditional_BA'] = np.where(results['AB_before'] > 0, results['H_before'] / results['AB_before'], np.nan)
    results['conditional_SLG'] = np.where(results['AB_before'] > 0, results['TB_before'] / results['AB_before'], np.nan)
    
    denom_obp_before = results['AB_before'] + results['BB_before'] + results['HBP_before'] + results['SF_before']
    results['conditional_OBP'] = np.where(
        denom_obp_before > 0,
        (results['H_before'] + results['BB_before'] + results['HBP_before']) / denom_obp_before,
        np.nan
    )
    
    results['conditional_Barrel_PA'] = np.where(
        results['num_PAs'] > 0,
        results['Barrels_before'] / results['num_PAs'],
        np.nan
    )
    
    results['conditional_Pitch_PA'] = np.where(
        results['num_PAs'] > 0,
        results['pitches_sum_before'] / results['num_PAs'],
        np.nan
    )
    
    results['conditional_delta_run_exp_PA'] = np.where(
        results['num_PAs'] > 0,
        results['delta_run_exp_sum_before'] / results['num_PAs'],
        np.nan
    )
    
    # Create Nitro_med_xy tuple
    results['focal_Nitro_med_xy'] = list(zip(results['nitro_x'], results['nitro_z']))
    results = results.drop(columns=['nitro_x', 'nitro_z'])
    
    # ============================================================
    # Calculate comprehensive Statcast metrics for each condition
    # ============================================================
    print("\nCalculating comprehensive Statcast metrics for conditional pairs...")
    print("(This may take several minutes depending on cache...)")
    
    cache_dir = Path(pitch_cache_dir)
    
    # Create a mapping of game_pk to the conditional batter for each focal batter
    if 'game_pk' in d.columns:
        game_id_col = 'game_pk'
    else:
        d['temp_game_id'] = d['game_date'].astype(str) + '_' + d['team'].astype(str)
        game_id_col = 'temp_game_id'
    
    # Build mapping: focal_batter -> {(conditional_batter, focal_side, cond_side) -> set of game_pks}
    focal_to_conditional_games = {}
    for _, row in d.iterrows():
        focal_id = int(row['batter'])
        cond_id = int(row['batter_before']) if pd.notna(row['batter_before']) else None
        focal_side = row['stand']
        cond_side = row['stand_before']
        game_id = row[game_id_col]
        
        if cond_id is None or pd.isna(cond_side):
            continue
            
        if focal_id not in focal_to_conditional_games:
            focal_to_conditional_games[focal_id] = {}
        key = (cond_id, focal_side, cond_side)
        if key not in focal_to_conditional_games[focal_id]:
            focal_to_conditional_games[focal_id][key] = set()
        focal_to_conditional_games[focal_id][key].add(game_id)
    
    # Now calculate comprehensive metrics for each row in results
    statcast_data = []
    
    total_pairs = len(results)
    for idx, row in results.iterrows():
        focal_id = int(row['focal_batter_id'])
        cond_id = int(row['conditional_batter_id'])
        focal_side = row['focal_HitterSide']
        cond_side = row['conditional_HitterSide']
        
        # Load cached pitch data for focal batter
        cache_path = cache_dir / f"{focal_id}_{start_date}_{end_date}.parquet"
        
        if idx < 5:
            print("\nDEBUG focal_id:", focal_id)
            print("DEBUG cond_id:", cond_id)
            print("DEBUG focal_side:", focal_side)
            print("DEBUG cond_side:", cond_side)
            print("DEBUG cache exists:", cache_path.exists())
        
        if not cache_path.exists():
            # No pitch data available - fill with NaN
            empty_metrics = {
                'focal_Swing_pct': np.nan, 'focal_Contact_pct': np.nan,
                'focal_SweetSpot_pct': np.nan, 'focal_SwStr_pct': np.nan, 'focal_Chase_pct': np.nan
            }
            if include_bat_tracking:
                empty_metrics.update({
                    'focal_Attack_Angle_median': np.nan,
                    'focal_Attack_Direction_median': np.nan,
                    'focal_Swing_Path_Tilt_median': np.nan,
                    'focal_Stance_Angle_median': np.nan,
                    'focal_Distance_Off_Plate_median': np.nan
                })
            statcast_data.append(empty_metrics)
            continue
        
        try:
            pitch_data = pd.read_parquet(cache_path)
        except:
            empty_metrics = {
                'focal_Swing_pct': np.nan, 'focal_Contact_pct': np.nan,
                'focal_SweetSpot_pct': np.nan, 'focal_SwStr_pct': np.nan, 'focal_Chase_pct': np.nan
            }
            if include_bat_tracking:
                empty_metrics.update({
                    'focal_Attack_Angle_median': np.nan,
                    'focal_Attack_Direction_median': np.nan,
                    'focal_Swing_Path_Tilt_median': np.nan,
                    'focal_Stance_Angle_median': np.nan,
                    'focal_Distance_Off_Plate_median': np.nan
                })
            statcast_data.append(empty_metrics)
            continue
        
        # Filter to only games where conditional batter batted before focal batter with these specific sides
        key = (cond_id, focal_side, cond_side)
        if focal_id in focal_to_conditional_games and key in focal_to_conditional_games[focal_id]:
            relevant_games = focal_to_conditional_games[focal_id][key]
            # Filter by games AND by batting side
            filtered_pitches = pitch_data[
                (pitch_data['game_pk'].isin(relevant_games)) & 
                (pitch_data['stand'] == focal_side)
            ]
            if idx < 5:
                print("DEBUG relevant_games count:", len(relevant_games) if 'relevant_games' in locals() else 0)
                print("DEBUG filtered_pitches rows:", len(filtered_pitches))
                print("DEBUG pitch_data rows:", len(pitch_data))
                print("DEBUG pitch_data columns:", pitch_data.columns.tolist())
            
                if 'stand' in pitch_data.columns:
                    print("DEBUG pitch stand unique:", pitch_data['stand'].dropna().unique())
            
                if 'game_pk' in pitch_data.columns:
                    print("DEBUG pitch game_pk dtype:", pitch_data['game_pk'].dtype)
                    print("DEBUG sample pitch game_pk:", pitch_data['game_pk'].dropna().head().tolist())
            
                print("DEBUG sample relevant_games:", list(relevant_games)[:5] if 'relevant_games' in locals() else [])
        else:
            filtered_pitches = pd.DataFrame()
        
        # Calculate focal batter conditional metrics
        focal_metrics_raw = compute_comprehensive_swing_metrics(filtered_pitches)
        focal_metrics = {f'focal_{k}': v for k, v in focal_metrics_raw.items()}
    
        # Calculate conditional batter metrics from the conditional batter's own pitch file
        conditional_cache_path = cache_dir / f"{cond_id}_{start_date}_{end_date}.parquet"
    
        if conditional_cache_path.exists():
            try:
                conditional_pitch_data = pd.read_parquet(conditional_cache_path)
    
                # Same relevant games, but filter to the conditional batter's hitting side
                conditional_filtered_pitches = conditional_pitch_data[
                    (conditional_pitch_data['game_pk'].isin(relevant_games)) &
                    (conditional_pitch_data['stand'] == cond_side)
                ]
    
                conditional_metrics_raw = compute_comprehensive_swing_metrics(conditional_filtered_pitches)
                conditional_metrics = {f'conditional_{k}': v for k, v in conditional_metrics_raw.items()}
                
                # Calculate conditional Nitro zone from barrels in these games
                if 'is_barrel' in conditional_filtered_pitches.columns:
                    barrels = conditional_filtered_pitches[conditional_filtered_pitches['is_barrel'] == 1]
                    if len(barrels) > 0 and 'plate_x' in barrels.columns and 'plate_z' in barrels.columns:
                        conditional_nitro_x = barrels['plate_x'].median()
                        conditional_nitro_z = barrels['plate_z'].median()
                        conditional_metrics['conditional_Nitro_med_xy'] = (conditional_nitro_x, conditional_nitro_z)
                    else:
                        conditional_metrics['conditional_Nitro_med_xy'] = (np.nan, np.nan)
                else:
                    conditional_metrics['conditional_Nitro_med_xy'] = (np.nan, np.nan)
            except:
                conditional_metrics = {
                    'conditional_Swing_pct': np.nan,
                    'conditional_Contact_pct': np.nan,
                    'conditional_SweetSpot_pct': np.nan,
                    'conditional_SwStr_pct': np.nan,
                    'conditional_Chase_pct': np.nan,
                    'conditional_GroundBall_pct': np.nan,
                    'conditional_FlyBall_pct': np.nan,
                    'conditional_LineDrive_pct': np.nan,
                    'conditional_PopUp_pct': np.nan,
                    'conditional_Attack_Angle_median': np.nan,
                    'conditional_Attack_Direction_median': np.nan,
                    'conditional_Swing_Path_Tilt_median': np.nan,
                    'conditional_Nitro_med_xy': (np.nan, np.nan),
                }
        else:
            conditional_metrics = {
                'conditional_Swing_pct': np.nan,
                'conditional_Contact_pct': np.nan,
                'conditional_SweetSpot_pct': np.nan,
                'conditional_SwStr_pct': np.nan,
                'conditional_Chase_pct': np.nan,
                'conditional_GroundBall_pct': np.nan,
                'conditional_FlyBall_pct': np.nan,
                'conditional_LineDrive_pct': np.nan,
                'conditional_PopUp_pct': np.nan,
                'conditional_Attack_Angle_median': np.nan,
                'conditional_Attack_Direction_median': np.nan,
                'conditional_Swing_Path_Tilt_median': np.nan,
                'conditional_Nitro_med_xy': (np.nan, np.nan),
            }
    
        # If not including bat tracking, remove those keys from both dicts
        if not include_bat_tracking:
            focal_bat_tracking_keys = [
                'focal_Attack_Angle_median', 'focal_Attack_Direction_median',
                'focal_Swing_Path_Tilt_median'
            ]
            conditional_bat_tracking_keys = [
                'conditional_Attack_Angle_median', 'conditional_Attack_Direction_median',
                'conditional_Swing_Path_Tilt_median'
            ]
    
            for key in focal_bat_tracking_keys:
                focal_metrics.pop(key, None)
            for key in conditional_bat_tracking_keys:
                conditional_metrics.pop(key, None)
    
        statcast_data.append({**focal_metrics, **conditional_metrics})
        
        if (idx + 1) % 50 == 0 or (idx + 1) == total_pairs:
                print(f"  Processed {idx + 1}/{total_pairs} conditional pairs")
    
    # Add statcast columns to results
    statcast_df = pd.DataFrame(statcast_data)
    results = pd.concat([results.reset_index(drop=True), statcast_df], axis=1)
    
    # Add player names
    focal_names = baselines[['batter', 'player_name']].drop_duplicates('batter').rename(
        columns={'batter': 'focal_batter_id', 'player_name': 'focal_batter_name'}
    )
    conditional_names = baselines[['batter', 'player_name']].drop_duplicates('batter').rename(
        columns={'batter': 'conditional_batter_id', 'player_name': 'conditional_batter_name'}
    )
    
    results = results.merge(focal_names, on='focal_batter_id', how='left')
    results = results.merge(conditional_names, on='conditional_batter_id', how='left')
    
    # Add overall season stats for focal player (for comparison with conditional stats)
    # Determine which columns exist in baselines
    season_cols = ['batter', 'HitterSide', 'PA', 'Barrel_PA', 'Pitch_PA', 
                   'BA', 'OBP', 'SLG', 'delta_run_exp_PA', 'Swing_pct', 'Contact_pct', 
                   'Nitro_med_xy']
    
    # Add comprehensive metrics if they exist
    if include_bat_tracking:
        comprehensive_cols = ['SweetSpot_pct', 'SwStr_pct', 'Chase_pct',
                            'GroundBall_pct', 'FlyBall_pct', 'LineDrive_pct', 'PopUp_pct',
                            'Attack_Angle_median', 'Attack_Direction_median', 
                            'Swing_Path_Tilt_median']
        season_cols.extend([c for c in comprehensive_cols if c in baselines.columns])
    
    # Only use columns that actually exist in baselines
    available_season_cols = [c for c in season_cols if c in baselines.columns]
    
    focal_season_stats = baselines[available_season_cols].copy()
    
    # Rename columns
    rename_dict = {'batter': 'focal_batter_id', 'HitterSide': 'focal_HitterSide'}
    for col in available_season_cols:
        if col not in ['batter', 'HitterSide']:
            rename_dict[col] = f'focal_season_{col}'
    
    focal_season_stats = focal_season_stats.rename(columns=rename_dict)
    results = results.merge(focal_season_stats, on=['focal_batter_id', 'focal_HitterSide'], how='left')
    
    # Add conditional season stats for comparison
    conditional_season_cols = ['batter', 'HitterSide', 'PA', 'Barrel_PA', 'Pitch_PA', 
                              'BA', 'OBP', 'SLG', 'delta_run_exp_PA', 'Swing_pct', 'Contact_pct', 
                              'Nitro_med_xy']
    
    if include_bat_tracking:
        comprehensive_cols_cond = ['SweetSpot_pct', 'SwStr_pct', 'Chase_pct',
                                  'GroundBall_pct', 'FlyBall_pct', 'LineDrive_pct', 'PopUp_pct',
                                  'Attack_Angle_median', 'Attack_Direction_median', 
                                  'Swing_Path_Tilt_median']
        conditional_season_cols.extend([c for c in comprehensive_cols_cond if c in baselines.columns])
    
    # Only use columns that actually exist in baselines
    available_conditional_season_cols = [c for c in conditional_season_cols if c in baselines.columns]
    
    conditional_season_stats = baselines[available_conditional_season_cols].copy()
    
    # Rename columns
    rename_dict_cond = {'batter': 'conditional_batter_id', 'HitterSide': 'conditional_HitterSide'}
    for col in available_conditional_season_cols:
        if col not in ['batter', 'HitterSide']:
            rename_dict_cond[col] = f'conditional_season_{col}'
    
    conditional_season_stats = conditional_season_stats.rename(columns=rename_dict_cond)
    results = results.merge(conditional_season_stats, on=['conditional_batter_id', 'conditional_HitterSide'], how='left')
    
    # Reorder columns - all focal stats first, then all conditional stats
    base_cols = ['focal_batter_id', 'focal_batter_name', 'focal_HitterSide',
                 'conditional_batter_id', 'conditional_batter_name', 'conditional_HitterSide',
                 'num_PAs']
    
    # Focal conditional stats
    focal_cond_cols = ['focal_Barrel_PA', 'focal_Pitch_PA', 'focal_BA', 'focal_OBP', 'focal_SLG',
                       'focal_delta_run_exp_PA', 'focal_Swing_pct', 'focal_Contact_pct']
    
    if include_bat_tracking:
        focal_cond_cols.extend(['focal_SweetSpot_pct', 'focal_SwStr_pct', 'focal_Chase_pct',
                               'focal_GroundBall_pct', 'focal_FlyBall_pct', 
                               'focal_LineDrive_pct', 'focal_PopUp_pct',
                               'focal_Attack_Angle_median', 'focal_Attack_Direction_median',
                               'focal_Swing_Path_Tilt_median'])
    
    focal_cond_cols.extend(['focal_Nitro_med_xy'])
    
    # Focal season stats (interleaved with conditional)
    focal_season_cols = []
    for metric in ['Barrel_PA', 'Pitch_PA', 'BA', 'OBP', 'SLG', 'delta_run_exp_PA', 
                   'Swing_pct', 'Contact_pct']:
        if f'focal_season_{metric}' in results.columns:
            focal_season_cols.append(f'focal_season_{metric}')
    
    if include_bat_tracking:
        for metric in ['SweetSpot_pct', 'SwStr_pct', 'Chase_pct',
                      'GroundBall_pct', 'FlyBall_pct', 'LineDrive_pct', 'PopUp_pct',
                      'Attack_Angle_median', 'Attack_Direction_median',
                      'Swing_Path_Tilt_median']:
            if f'focal_season_{metric}' in results.columns:
                focal_season_cols.append(f'focal_season_{metric}')
    
    if 'focal_season_Nitro_med_xy' in results.columns:
        focal_season_cols.append('focal_season_Nitro_med_xy')
    
    if 'focal_season_PA' in results.columns:
        focal_season_cols.insert(0, 'focal_season_PA')
    
    # Conditional stats - including comprehensive metrics
    conditional_cols = ['conditional_Barrel_PA', 'conditional_Pitch_PA', 'conditional_BA',
                       'conditional_OBP', 'conditional_SLG', 'conditional_delta_run_exp_PA',
                       'conditional_Swing_pct', 'conditional_Contact_pct']
    
    if include_bat_tracking:
        conditional_cols.extend(['conditional_SweetSpot_pct', 'conditional_SwStr_pct', 'conditional_Chase_pct',
                                'conditional_GroundBall_pct', 'conditional_FlyBall_pct',
                                'conditional_LineDrive_pct', 'conditional_PopUp_pct',
                                'conditional_Attack_Angle_median', 'conditional_Attack_Direction_median',
                                'conditional_Swing_Path_Tilt_median'])
    
    conditional_cols.extend(['conditional_Nitro_med_xy'])
    
    # Build final column order: ALL FOCAL FIRST, THEN ALL CONDITIONAL
    focal_cols_ordered = []
    
    # Add focal conditional stats
    for cond_col in focal_cond_cols:
        if cond_col in results.columns:
            focal_cols_ordered.append(cond_col)
    
    # Add ALL focal season stats after focal conditional stats
    for season_col in focal_season_cols:
        if season_col in results.columns:
            focal_cols_ordered.append(season_col)
    
    # Add any remaining focal season cols not in the list
    for col in results.columns:
        if col.startswith('focal_season_') and col not in focal_cols_ordered:
            focal_cols_ordered.append(col)
    
    # Now add conditional stats (all together at the end)
    conditional_cols_ordered = [c for c in conditional_cols if c in results.columns]
    
    # Add conditional season stats after conditional conditional stats
    conditional_season_cols_ordered = []
    for col in results.columns:
        if col.startswith('conditional_season_'):
            conditional_season_cols_ordered.append(col)
    
    final_cols = base_cols + focal_cols_ordered + conditional_cols_ordered + conditional_season_cols_ordered
    other_cols = [c for c in results.columns if c not in final_cols]
    results = results[final_cols + other_cols]
    
    # Sort
    results = results.sort_values(['focal_batter_id', 'num_PAs'], 
                                   ascending=[True, False]).reset_index(drop=True)
    
    # Drop intermediate calculation columns
    cols_to_drop = ['H', 'TB', 'AB', 'BB', 'HBP', 'SF', 'Barrels', 'pitches_sum', 'delta_run_exp_sum',
                    'H_before', 'TB_before', 'AB_before', 'BB_before', 'HBP_before', 'SF_before', 
                    'Barrels_before', 'pitches_sum_before', 'delta_run_exp_sum_before']
    results = results.drop(columns=[c for c in cols_to_drop if c in results.columns])
    
    return results