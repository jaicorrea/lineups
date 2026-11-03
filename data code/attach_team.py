"""Attach each pair's team (and a cross-team flag) to the pooled pair data -> ..._pooled_all_team.csv"""
import pandas as pd
from pathlib import Path

R = Path(__file__).resolve().parent.parent  # repo root
dirs = {2023: "statcast hitters 2023", 2024: "statcast hitters 2024", 2025: "statcast hitters 2025", 2026: "statcast hitters 2026"}
keys = ["season", "focal_batter_id", "focal_HitterSide", "conditional_batter_id", "conditional_HitterSide"]
frames = []
for yr, dn in dirs.items():
    parts = []
    for f in sorted((R / dn).glob("*.csv")):
        d = pd.read_csv(f, usecols=["batter", "stand", "game_pk", "at_bat_number", "inning_topbot", "home_team", "away_team", "events"])
        d = d[d["events"] != "truncated_pa"]   # dropped in every season (would make a batter his own predecessor)
        d["file_team"] = f.stem.upper()
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    top = df["inning_topbot"].astype(str).str.lower().str.startswith("top")
    df["bt"] = df["away_team"].where(top, df["home_team"])
    df = df.sort_values(["game_pk", "at_bat_number"]).reset_index(drop=True)
    g = df.groupby(["game_pk", "bt"])
    df["batter_before"] = g["batter"].shift(1)
    df["stand_before"] = g["stand"].shift(1)
    d = df.dropna(subset=["batter_before", "stand_before"])
    p = (d.groupby(["batter", "stand", "batter_before", "stand_before", "file_team"]).size().rename("n").reset_index())
    p["batter_before"] = p["batter_before"].astype("int64")
    p = p.sort_values("n", ascending=False)
    k4 = ["batter", "stand", "batter_before", "stand_before"]
    nteams = p.groupby(k4).file_team.nunique().rename("nteams")
    top_team = p.drop_duplicates(k4).set_index(k4)
    out = top_team[["file_team"]].join(nteams).reset_index()
    out.columns = ["focal_batter_id", "focal_HitterSide", "conditional_batter_id", "conditional_HitterSide", "team", "nteams"]
    out["team_cross_team_pair"] = (out["nteams"] > 1).astype(int)
    out["season"] = yr
    frames.append(out.drop(columns="nteams"))
tm = pd.concat(frames, ignore_index=True)
pooled = pd.read_csv(R / "data" / "pooled" / "conditional_stats_with_baselines_pooled_all.csv", low_memory=False)
n0 = len(pooled)
merged = pooled.merge(tm, on=keys, how="left", validate="one_to_one")
assert len(merged) == n0
print("pooled rows", n0, "| rows without a team:", int(merged.team.isna().sum()), "| cross-team pairs:", int(merged.team_cross_team_pair.sum()))
merged.to_csv(R / "data" / "pooled" / "conditional_stats_with_baselines_pooled_all_team.csv", index=False)
