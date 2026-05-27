# -*- coding: utf-8 -*-
"""
Created on Thu Feb  5 13:35:47 2026

@author: jaico
"""

from pathlib import Path
import pandas as pd

folder = Path(__file__).parent.parent / "statcast hitters"
dfs = []

for f in folder.glob("*.csv"):
    team = f.stem.upper()
    d = pd.read_csv(f)
    d["team"] = team
    dfs.append(d)

df = pd.concat(dfs, ignore_index=True)
