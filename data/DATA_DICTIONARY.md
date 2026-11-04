# Data dictionary: `data/pooled/conditional_stats_with_woba_pooled_all_team.csv`

The analysis dataset. One row per (season, focal hitter, conditional hitter) pair, with a separate row for each batting side of a switch-hitter. 2025 and 2026 stacked (about 19,900 rows). All regressions in `analysis/` read this file. It is the pooled pair table (`pool_seasons.py`) plus team columns (`attach_team.py`) plus pair wOBA columns (`build_woba_outcomes.py`).

**Focal** hitter = the batter; **conditional** hitter = the batter who hit directly before him on the same team in the same game (the paper's "predecessor"). Truncated PAs (`events == 'truncated_pa'`) are dropped before pairing.

## Pair-level columns (no prefix)

| Column | Meaning |
|---|---|
| `season` | 2025 or 2026 |
| `num_PAs` | Plate appearances in which the focal hitter batted directly behind the conditional hitter; the regression weight |
| `nitro_dist` | Euclidean distance between the two hitters' season nitro points: `sqrt((focal_season_nitro_x - conditional_season_nitro_x)^2 + (focal_season_nitro_z - conditional_season_nitro_z)^2)` |
| `team` | Team the pair played for (the team file in which the pair occurs most) |
| `team_cross_team_pair` | 1 if the pair appears under more than one team in the season (a traded hitter), else 0 |
| `woba_pair` | Pair wOBA of the focal hitter in these PAs: `sum(woba_value) / sum(woba_denom)` |
| `xwoba_pair` | Same with `estimated_woba_using_speedangle` in the numerator |
| `woba_den` | Denominator used for the two wOBA columns (`sum(woba_denom)`) |
| `woba_pa_mismatch` | 1 if the PA count rebuilt in `build_woba_outcomes.py` disagrees with `num_PAs`; `table1_regressions.R` drops these rows for the wOBA outcome |

## `focal_*` and `conditional_*` columns

Every column below exists once with the `focal_` prefix and once with `conditional_`.

**Identity**: `batter_id`, `batter_name`, `HitterSide` (batting side for this row; a switch-hitter appears once per side).

**Pair-specific outcomes** (computed only over the PAs of this pair, so they vary by pair):

| Column | Meaning |
|---|---|
| `Barrel_PA` | Barrels per PA (Statcast `launch_speed_angle == 6`) |
| `Pitch_PA` | Pitches seen per PA |
| `BA`, `OBP`, `SLG` | Batting average, on-base percentage, slugging |
| `delta_run_exp_PA` | Mean change in run expectancy per PA, summed over every pitch of the PA (full-PA run value, not just the final pitch) |
| `Swing_pct`, `Contact_pct`, `SwStr_pct`, `Chase_pct` | Swing%, contact% (of swings), swinging-strike%, chase% (swings at pitches out of the zone) |
| `SweetSpot_pct`, `GroundBall_pct`, `FlyBall_pct`, `LineDrive_pct`, `PopUp_pct` | Share of batted balls with a launch angle of 8 to 32 degrees, and share by batted-ball type |
| `Attack_Angle_median`, `Attack_Direction_median`, `Swing_Path_Tilt_median` | Median bat-tracking metrics over the hitter's swings |
| `Nitro_med_xy`, `nitro_x`, `nitro_z` | Median plate location (horizontal, vertical) of the hitter's barrels in these PAs; `Nitro_med_xy` is the `(x, z)` tuple |

**Season baselines** (`focal_season_*`, `conditional_season_*`): the same metrics computed over the hitter's whole season (and side), with `season_PA` the season PA total and `season_nitro_x` / `season_nitro_z` the season nitro point. The regressions use these baselines as the traits, z-scored within season. Only hitters with at least 50 PA in the season are kept.

## Where the paper's trait names come from

| Paper trait | Column stem (prefixed `focal_season_` / `conditional_season_`) |
|---|---|
| OBP, SLG, Barrel/PA, Pitch/PA | `OBP`, `SLG`, `Barrel_PA`, `Pitch_PA` |
| Swing%, Chase%, Contact%, Swinging-strike% | `Swing_pct`, `Chase_pct`, `Contact_pct`, `SwStr_pct` |
| Sweet spot%, Line-drive% | `SweetSpot_pct`, `LineDrive_pct` |
| Attack angle, Attack direction, Swing path tilt | `Attack_Angle_median`, `Attack_Direction_median`, `Swing_Path_Tilt_median` |
| Nitro dist | `nitro_dist` (pair-level) |
| Absolute contact gap | `abs(conditional_season_Contact_pct - focal_season_Contact_pct)` (built in `table1_regressions.R`) |
