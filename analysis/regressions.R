# R translation of regressions.do
# Note: conditional_stats_with_baselines.csv was never generated on disk
# (it's the output of `data code/tablesort_scratch.py`). Its columns are a
# superset of conditional_lineup_stats_2025.csv, so that file is used here.

library(readr)
library(dplyr)
library(fixest)

df <- read_csv("../conditional_lineup_stats_2025.csv", show_col_types = FALSE)
names(df) <- tolower(names(df))  # Stata's `import delimited` lowercases names

df <- df %>%
  mutate(focal_delta_run_diff = focal_delta_run_exp_pa - focal_season_delta_run_exp_pa)

# -----------------------------------------------------------------------------
# Basic diagnostics: check if "season" traits vary within player IDs
# -----------------------------------------------------------------------------
df <- df %>%
  group_by(conditional_batter_id) %>%
  mutate(sd_cond_season_obp = sd(conditional_season_obp, na.rm = TRUE)) %>%
  ungroup() %>%
  group_by(focal_batter_id) %>%
  mutate(sd_focal_season_slg = sd(focal_season_slg, na.rm = TRUE)) %>%
  ungroup()

cat("Rows with within-conditional_id variation in conditional_season_obp: ",
    sum(df$sd_cond_season_obp > 0 & !is.na(df$sd_cond_season_obp)), "\n")
cat("Rows with within-focal_id variation in focal_season_slg: ",
    sum(df$sd_focal_season_slg > 0 & !is.na(df$sd_focal_season_slg)), "\n")

# -----------------------------------------------------------------------------
# Pairing-mechanism proxies
# -----------------------------------------------------------------------------
zscore <- function(x) as.numeric(scale(x))

df <- df %>%
  mutate(
    cond_take_pct   = 1 - conditional_season_swing_pct,
    same_side       = ifelse(!is.na(focal_hitterside) & !is.na(conditional_hitterside),
                              as.numeric(focal_hitterside == conditional_hitterside), NA),
    opp_side        = ifelse(!is.na(same_side), 1 - same_side, NA),
    swing_gap       = focal_season_swing_pct - conditional_season_swing_pct,
    contact_gap     = focal_season_contact_pct - conditional_season_contact_pct,
    chase_gap       = focal_season_chase_pct - conditional_season_chase_pct,
    swstr_gap       = focal_season_swstr_pct - conditional_season_swstr_pct,
    abs_swing_gap   = abs(swing_gap),
    abs_contact_gap = abs(contact_gap),
    abs_chase_gap   = abs(chase_gap),
    abs_swstr_gap   = abs(swstr_gap),
    z_cond_obp        = zscore(conditional_season_obp),
    z_cond_take       = zscore(cond_take_pct),
    z_cond_contact    = zscore(conditional_season_contact_pct),
    z_cond_barrel     = zscore(conditional_season_barrel_pa),
    z_focal_slg       = zscore(focal_season_slg),
    z_focal_barrel    = zscore(focal_season_barrel_pa),
    z_abs_swing_gap   = zscore(abs_swing_gap),
    z_abs_contact_gap = zscore(abs_contact_gap),
    z_abs_chase_gap   = zscore(abs_chase_gap),
    z_abs_swstr_gap   = zscore(abs_swstr_gap),
    z_contact_gap     = zscore(contact_gap),   # signed
    z_obp = zscore(conditional_season_obp),
    z_slg = zscore(focal_season_slg)
  )

stopifnot(all(df$num_pas == floor(df$num_pas)))

hr <- function(label, model) {
  cat("\n==============================\n", label, "\n==============================\n")
  print(summary(model))
}

# 1) reg focal_delta_run_exp_pa c.conditional_season_obp##c.focal_season_slg
hr("[1] focal_delta_run_exp_pa ~ conditional_season_obp * focal_season_slg",
   lm(focal_delta_run_exp_pa ~ conditional_season_obp * focal_season_slg, data = df))

# 2) reg focal_delta_run_diff conditional_season_obp
hr("[2] focal_delta_run_diff ~ conditional_season_obp",
   lm(focal_delta_run_diff ~ conditional_season_obp, data = df))

# 3) reg focal_delta_run_diff c.conditional_season_obp##c.focal_season_slg
hr("[3] focal_delta_run_diff ~ conditional_season_obp * focal_season_slg",
   lm(focal_delta_run_diff ~ conditional_season_obp * focal_season_slg, data = df))

# 4) reg ... [aweight=num_pas], vce(cluster focal_batter_id)
hr("[4] [3] with aweight=num_pas, cluster(focal_batter_id)",
   feols(focal_delta_run_diff ~ conditional_season_obp * focal_season_slg,
         data = df, weights = ~num_pas, cluster = ~focal_batter_id))

# 5) reghdfe focal_delta_run_exp_pa ... [fw=num_pas] if num_pas>50, absorb(focal conditional) cluster(focal)
hr("[5] reghdfe: focal_delta_run_exp_pa ~ obp*slg | focal+conditional FE, num_pas>50",
   feols(focal_delta_run_exp_pa ~ conditional_season_obp * focal_season_slg |
           focal_batter_id + conditional_batter_id,
         data = df %>% filter(num_pas > 50), weights = ~num_pas, cluster = ~focal_batter_id))

# 6) reg focal_delta_run_diff c.z_obp##c.z_slg
hr("[6] focal_delta_run_diff ~ z_obp * z_slg",
   lm(focal_delta_run_diff ~ z_obp * z_slg, data = df))

# 7) xtile quartiles, reg with factor interactions
df <- df %>%
  mutate(
    q_obp = ntile(conditional_season_obp, 4),
    q_slg = ntile(focal_season_slg, 4)
  )
hr("[7] focal_delta_run_diff ~ factor(q_obp) * factor(q_slg)",
   lm(focal_delta_run_diff ~ factor(q_obp) * factor(q_slg), data = df))

# -----------------------------------------------------------------------------
# Complementarity battery (fixest::feols == reghdfe)
# -----------------------------------------------------------------------------
fe_reg <- function(label, rhs, data = df, wgt = ~num_pas) {
  fml <- as.formula(paste0("focal_delta_run_exp_pa ~ ", rhs,
                            " | focal_batter_id + conditional_batter_id"))
  hr(label, feols(fml, data = data, weights = wgt, cluster = ~focal_batter_id))
}

fe_reg("[0] Baseline: z_cond_obp * z_focal_slg", "z_cond_obp * z_focal_slg")
fe_reg("[1] Discipline -> Power: z_cond_take * z_focal_slg", "z_cond_take * z_focal_slg")
fe_reg("[2] Contact -> Power: z_cond_contact * z_focal_slg", "z_cond_contact * z_focal_slg")
fe_reg("[3] Prior hard-contact -> focal power: z_cond_barrel * z_focal_slg", "z_cond_barrel * z_focal_slg")
fe_reg("[4] OBP -> focal barrel skill: z_cond_obp * z_focal_barrel", "z_cond_obp * z_focal_barrel")
fe_reg("[5] Handedness sequencing: opp_side * z_focal_slg", "factor(opp_side) * z_focal_slg")
fe_reg("[6a] Approach contrast (swing gap): z_abs_swing_gap * z_focal_slg", "z_abs_swing_gap * z_focal_slg")
fe_reg("[6b] Approach contrast (contact gap): z_abs_contact_gap * z_focal_slg", "z_abs_contact_gap * z_focal_slg")

# 7) Higher-support sample only (num_pas > 50)
df_hi <- df %>% filter(num_pas > 50)
fe_reg("[7a] z_cond_obp * z_focal_slg, num_pas>50", "z_cond_obp * z_focal_slg", data = df_hi)
fe_reg("[7b] z_cond_take * z_focal_slg, num_pas>50", "z_cond_take * z_focal_slg", data = df_hi)
fe_reg("[7c] z_abs_contact_gap * z_focal_slg, num_pas>50", "z_abs_contact_gap * z_focal_slg", data = df_hi)

# PA-cutoff robustness sweep for tier 2/3 findings
df_hi40 <- df %>% filter(num_pas > 40)
df_hi75 <- df %>% filter(num_pas > 75)

fe_reg("[7c-40] z_abs_contact_gap * z_focal_slg, num_pas>40", "z_abs_contact_gap * z_focal_slg", data = df_hi40)
fe_reg("[7c-75] z_abs_contact_gap * z_focal_slg, num_pas>75", "z_abs_contact_gap * z_focal_slg", data = df_hi75)

fe_reg("[7b-40] z_cond_take * z_focal_slg, num_pas>40", "z_cond_take * z_focal_slg", data = df_hi40)
fe_reg("[7b-75] z_cond_take * z_focal_slg, num_pas>75", "z_cond_take * z_focal_slg", data = df_hi75)

# =============================================================================
# TIER A: validation of the one durable finding (|contact gap| x focal SLG)
# =============================================================================

# --- A1: Signed contact gap x SLG -- does DIRECTION matter, or pure dissimilarity?
#     (full, then num_pas>50). z_contact_gap is signed: +ve = focal makes MORE
#     contact than predecessor, -ve = focal makes LESS.
fe_reg("[A1] signed z_contact_gap * z_focal_slg (full)", "z_contact_gap * z_focal_slg")
fe_reg("[A1r] signed z_contact_gap * z_focal_slg, num_pas>50", "z_contact_gap * z_focal_slg", data = df_hi)

# --- A2: Does "approach dissimilarity amplifies power" generalize to OTHER gap
#     measures, or is it contact-specific? |swing|, |chase|, |swstr| gaps x SLG.
#     (swing gap already exists as [6a]; run all at full + >50 for comparability.)
fe_reg("[A2-swing]  z_abs_swing_gap * z_focal_slg (full)",  "z_abs_swing_gap * z_focal_slg")
fe_reg("[A2-swingr] z_abs_swing_gap * z_focal_slg, >50",    "z_abs_swing_gap * z_focal_slg", data = df_hi)
fe_reg("[A2-chase]  z_abs_chase_gap * z_focal_slg (full)",  "z_abs_chase_gap * z_focal_slg")
fe_reg("[A2-chaser] z_abs_chase_gap * z_focal_slg, >50",    "z_abs_chase_gap * z_focal_slg", data = df_hi)
fe_reg("[A2-swstr]  z_abs_swstr_gap * z_focal_slg (full)",  "z_abs_swstr_gap * z_focal_slg")
fe_reg("[A2-swstrr] z_abs_swstr_gap * z_focal_slg, >50",    "z_abs_swstr_gap * z_focal_slg", data = df_hi)

# --- A3: Split-half validation of |contact gap| x SLG.
#     Randomly partition the pairs into two halves; a real effect should hold
#     (same sign, ideally significant) in BOTH halves. Uses the full sample
#     (not >50) to keep each half adequately powered.
set.seed(20260824)
df_shuf <- df %>% mutate(.half = sample(rep(c(1L, 2L), length.out = n())))
fe_reg("[A3-h1] |contact gap| x SLG, split-half #1", "z_abs_contact_gap * z_focal_slg",
       data = df_shuf %>% filter(.half == 1))
fe_reg("[A3-h2] |contact gap| x SLG, split-half #2", "z_abs_contact_gap * z_focal_slg",
       data = df_shuf %>% filter(.half == 2))

# =============================================================================
# TIER B: is the |contact gap| x SLG effect platoon-driven?
#   opp_side = 1 if focal & predecessor bat from OPPOSITE sides, 0 if same.
# =============================================================================

# --- B1: three-way opp_side x |contact gap| x focal SLG (full, then >50).
#     A significant 3-way term = the contact-gap effect differs by handedness.
fe_reg("[B1] opp_side x |contact gap| x SLG (full)",
       "factor(opp_side) * z_abs_contact_gap * z_focal_slg")
fe_reg("[B1r] opp_side x |contact gap| x SLG, num_pas>50",
       "factor(opp_side) * z_abs_contact_gap * z_focal_slg", data = df_hi)

# --- B2: cleaner -- run |contact gap| x SLG SEPARATELY within same-side and
#     opposite-side pairs. If the effect lives in one handedness regime, that
#     shows which. Full sample used to keep each subset powered.
fe_reg("[B2-same] |contact gap| x SLG, SAME-side pairs only",
       "z_abs_contact_gap * z_focal_slg", data = df %>% filter(same_side == 1))
fe_reg("[B2-opp]  |contact gap| x SLG, OPPOSITE-side pairs only",
       "z_abs_contact_gap * z_focal_slg", data = df %>% filter(opp_side == 1))

# --- B3: does handedness alone interact with the contact gap (no power)?
fe_reg("[B3] opp_side x |contact gap| (full)",
       "factor(opp_side) * z_abs_contact_gap")
