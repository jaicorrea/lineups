from pathlib import Path
import pandas as pd, numpy as np, glob, os
os.chdir(Path(__file__).resolve().parent.parent)  # repo root
rng = np.random.default_rng(1)
REPS = 30
dirs = {2023: "statcast_pitch_cache_2023", 2024: "statcast_pitch_cache_2024", 2025: "statcast_pitch_cache_2025", 2026: "statcast_pitch_cache_2026"}
SW = {"swinging_strike","swinging_strike_blocked","foul","foul_tip","hit_into_play","hit_into_play_no_out","hit_into_play_score","foul_bunt","missed_bunt"}
CT = {"foul","hit_into_play","hit_into_play_no_out","hit_into_play_score","foul_bunt"}
SS = {"swinging_strike","swinging_strike_blocked","foul_tip","missed_bunt"}
BB = {"hit_into_play","hit_into_play_no_out","hit_into_play_score"}
pairs = pd.read_csv("data/pooled/conditional_stats_with_baselines_pooled_all_team.csv", usecols=["season","focal_batter_id","focal_season_PA","conditional_batter_id","conditional_season_PA"])
hs = pd.concat([pairs[["season","focal_batter_id","focal_season_PA"]].set_axis(["season","batter","pa"], axis=1),
                pairs[["season","conditional_batter_id","conditional_season_PA"]].set_axis(["season","batter","pa"], axis=1)]).drop_duplicates(["season","batter"])
hs = hs[hs.pa >= 50]
cols = ["batter","game_type","game_pk","at_bat_number","pitch_number","description","zone","events","launch_angle","bb_type","attack_angle","attack_direction","swing_path_tilt","launch_speed_angle"]
def sb(r): return 2*r/(1+r)
allrows = []
for yr, dr in dirs.items():
    keep = set(hs[hs.season == yr].batter)
    d = pd.concat([pd.read_parquet(f, columns=cols) for f in glob.glob(f"{dr}/*.parquet")], ignore_index=True)
    d = d[(d.game_type == "R") & d.batter.isin(keep)].dropna(subset=["game_pk","at_bat_number"]).copy()
    d["pa"] = d.groupby(["batter","game_pk","at_bat_number"]).ngroup()
    d["sw"] = d.description.isin(SW); d["ct"] = d.description.isin(CT); d["ss"] = d.description.isin(SS)
    d["chase_opp"] = d.zone.isin([11,12,13,14]); d["chase_sw"] = d.sw & d.chase_opp
    d["bbe"] = d.description.isin(BB)
    d["sweet"] = d.bbe & d.launch_angle.between(8, 32)
    for k, v in {"gb":"ground_ball","fb":"fly_ball","ld":"line_drive","pu":"popup"}.items(): d[k] = d.bbe & (d.bb_type == v)
    for c in ["attack_angle","attack_direction","swing_path_tilt"]: d["sw_"+c] = d[c].where(d.sw)
    # PA-level rows (final pitch of each PA)
    ev = d[d.events.notna() & (d.events != "truncated_pa")].drop_duplicates("pa", keep="last").copy()   # truncated PAs dropped in every season
    tb = {"single":1,"double":2,"triple":3,"home_run":4}
    ev["TB"] = ev.events.map(tb).fillna(0); ev["H"] = (ev.TB > 0).astype(int)
    ev["BBn"] = ev.events.isin(["walk","intent_walk"]).astype(int); ev["HBP"] = (ev.events == "hit_by_pitch").astype(int)
    ev["SF"] = (ev.events == "sac_fly").astype(int); ev["SAC"] = ev.events.isin(["sac_fly","sac_bunt"]).astype(int); ev["CI"] = (ev.events == "catcher_interf").astype(int)
    ev["AB"] = (1 - ev.BBn - ev.HBP - ev.SAC - ev.CI).clip(lower=0)
    ev["barrel"] = (pd.to_numeric(ev.launch_speed_angle, errors="coerce").eq(6).fillna(False)).astype(int)
    pa_ids = ev.pa.values; npa = d.pa.max() + 1
    res = {k: [] for k in ["Swing%","SwStr%","Contact%","Chase%","Sweet spot%","GB%","FB%","LD%","PU%","Attack angle","Attack direction","Swing path tilt","BA","OBP","SLG","Barrel/PA","Pitches/PA"]}
    for rep in range(REPS):
        lab = rng.integers(0, 2, npa)
        d["h"] = lab[d.pa.values]; ev["h"] = lab[ev.pa.values]
        g = d.groupby(["batter","h"])
        n = g.size(); s = g[["sw","ct","ss","chase_opp","chase_sw","bbe","sweet","gb","fb","ld","pu"]].sum()
        med = g[["sw_attack_angle","sw_attack_direction","sw_swing_path_tilt"]].median()
        e = ev.groupby(["batter","h"])[["H","TB","BBn","HBP","SF","AB","barrel","pitch_number"]].sum(); en = ev.groupby(["batter","h"]).size()
        m = pd.DataFrame({
            "Swing%": s.sw/n, "SwStr%": s.ss/n, "Contact%": s.ct/s.sw.replace(0,np.nan), "Chase%": s.chase_sw/s.chase_opp.replace(0,np.nan),
            "Sweet spot%": s.sweet/s.bbe.replace(0,np.nan), "GB%": s.gb/s.bbe.replace(0,np.nan), "FB%": s.fb/s.bbe.replace(0,np.nan),
            "LD%": s.ld/s.bbe.replace(0,np.nan), "PU%": s.pu/s.bbe.replace(0,np.nan),
            "Attack angle": med.sw_attack_angle, "Attack direction": med.sw_attack_direction, "Swing path tilt": med.sw_swing_path_tilt,
            "BA": e.H/e.AB.replace(0,np.nan), "OBP": (e.H+e.BBn+e.HBP)/(e.AB+e.BBn+e.HBP+e.SF).replace(0,np.nan),
            "SLG": e.TB/e.AB.replace(0,np.nan), "Barrel/PA": e.barrel/en, "Pitches/PA": e.pitch_number/en})
        for k in res:
            w = m[k].unstack("h").dropna()
            if len(w) > 20: res[k].append(sb(np.corrcoef(w[0], w[1])[0,1]))
    nh = d.batter.nunique()
    bbe_per = d[d.bbe].groupby("batter").size().mean(); sw_per = d[d.sw].groupby("batter").size().mean()
    for k, v in res.items(): allrows.append(dict(season=yr, trait=k, reliability=np.mean(v), hitters=nh))
    print(yr, "hitters", nh, "mean BBE", round(bbe_per), "mean swings", round(sw_per), flush=True)
out = pd.DataFrame(allrows)
tab = out.pivot(index="trait", columns="season", values="reliability"); tab["mean"] = tab.mean(axis=1)
order = ["Swing%","SwStr%","Chase%","Contact%","Attack angle","Attack direction","Swing path tilt","Sweet spot%","GB%","FB%","LD%","PU%","BA","OBP","SLG","Barrel/PA","Pitches/PA"]
tab = tab.loc[order].round(2); print(tab.to_string()); tab.to_csv("analysis/trait_reliability.csv"); print("hitter-seasons by season:", hs.groupby("season").size().to_dict())
