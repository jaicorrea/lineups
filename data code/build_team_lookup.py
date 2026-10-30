"""Build hitter x season x team lookup from the per-team pitch CSVs.

Output: team_lookup.csv with columns season, batter, team, pas (distinct PAs for that
batter with that team's CSV). Also checks that each file's batting team (derived from
inning_topbot/home_team/away_team) matches its filename.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIRS = {2023: "statcast hitters 2023 full", 2024: "statcast hitters 2024",
        2025: "statcast hitters", 2026: "statcast hitters 2026"}
COLS = ["batter", "game_pk", "at_bat_number", "game_type", "home_team", "away_team", "inning_topbot"]

rows, mism = [], []
for yr, dn in DIRS.items():
    for f in sorted((ROOT / dn).glob("*.csv")):
        d = pd.read_csv(f, usecols=lambda c: c in COLS, low_memory=False)
        if "game_type" in d:
            d = d[d["game_type"] == "R"]
        bat_team = d["home_team"].where(d["inning_topbot"] == "Bot", d["away_team"])
        file_team = f.stem.upper()
        mism.append((yr, file_team, bat_team.str.upper().ne(file_team).mean(), bat_team.mode().iat[0] if len(bat_team) else None))
        g = (d.drop_duplicates(["batter", "game_pk", "at_bat_number"])
               .groupby("batter").size().rename("pas").reset_index())
        g["season"], g["team"] = yr, file_team
        rows.append(g)
out = pd.concat(rows, ignore_index=True)
out.to_csv(ROOT / "team_lookup.csv", index=False)
m = pd.DataFrame(mism, columns=["season", "file_team", "share_batting_team_differs", "modal_batting_team"])
print(m[m.share_batting_team_differs > 0.01].to_string(index=False) or "all files: batting team == filename")
print(out.groupby("season").agg(files=("team", "nunique"), hitters=("batter", "nunique"), rows=("batter", "size")))
