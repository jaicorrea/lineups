# R translation of reducedformregs2.do

library(readr)
library(dplyr)
library(fixest)

df <- read_csv("../conditional_stats_with_baselines.csv", show_col_types = FALSE)
names(df) <- tolower(names(df))

zscore <- function(x) as.numeric(scale(x))

df <- df %>%
  mutate(
    cond_take_pct = 1 - conditional_season_swing_pct,

    z_cond_ss     = zscore(conditional_season_sweetspot_pct),
    z_cond_aa     = zscore(conditional_season_attack_angle_median),
    z_cond_ad     = zscore(conditional_season_attack_direction_median),
    z_cond_tilt   = zscore(conditional_season_swing_path_tilt_median),
    z_cond_gb     = zscore(conditional_season_groundball_pct),
    z_cond_fb     = zscore(conditional_season_flyball_pct),
    z_cond_ld     = zscore(conditional_season_linedrive_pct),
    z_cond_pu     = zscore(conditional_season_popup_pct),
    z_cond_chase  = zscore(conditional_season_chase_pct),
    z_cond_swstr  = zscore(conditional_season_swstr_pct),
    z_cond_take   = zscore(cond_take_pct),

    z_focal_ss    = zscore(focal_season_sweetspot_pct),
    z_focal_aa    = zscore(focal_season_attack_angle_median),
    z_focal_ad    = zscore(focal_season_attack_direction_median),
    z_focal_tilt  = zscore(focal_season_swing_path_tilt_median),
    z_focal_gb    = zscore(focal_season_groundball_pct),
    z_focal_fb    = zscore(focal_season_flyball_pct),
    z_focal_ld    = zscore(focal_season_linedrive_pct),
    z_focal_pu    = zscore(focal_season_popup_pct),
    z_focal_chase = zscore(focal_season_chase_pct),
    z_focal_swstr = zscore(focal_season_swstr_pct),
    z_focal_swing = zscore(focal_season_swing_pct),

    z_nitro_dist  = zscore(nitro_dist),

    z_cond_nitro_x  = zscore(conditional_season_nitro_x),
    z_focal_nitro_x = zscore(focal_season_nitro_x),
    z_cond_nitro_z  = zscore(conditional_season_nitro_z),
    z_focal_nitro_z = zscore(focal_season_nitro_z),

    z_cond_obp = zscore(conditional_season_obp),

    z_focal_slg = zscore(focal_season_slg),
    z_cond_slg  = zscore(conditional_season_slg),

    z_cond_contact = zscore(conditional_season_contact_pct),

    abs_contact_gap = abs(focal_season_contact_pct - conditional_season_contact_pct),
    z_abs_contact_gap = zscore(abs_contact_gap)
  )

hr <- function(label, model) {
  cat("\n==============================\n", label, "\n==============================\n")
  print(summary(model))
}

fe_reg <- function(label, rhs, data = df, wgt = ~num_pas) {
  fml <- as.formula(paste0("focal_delta_run_exp_pa ~ ", rhs,
                            " | focal_batter_id + conditional_batter_id"))
  hr(label, feols(fml, data = data, weights = wgt, cluster = ~focal_batter_id))
}

fe_reg("[1] Sweet spot (prior) x Attack angle (focal)",     "z_cond_ss * z_focal_aa")
fe_reg("[2] Line drive (prior) x Swing tilt (focal)",       "z_cond_ld * z_focal_tilt")
fe_reg("[3] Chase rate (prior) x Attack direction (focal)", "z_cond_chase * z_focal_ad")
fe_reg("[4] SwStr rate (prior) x Attack direction (focal)", "z_cond_swstr * z_focal_ad")
fe_reg("[5] Groundball rate (prior) x Attack angle (focal)","z_cond_gb * z_focal_aa")
fe_reg("[6] Flyball rate (prior) x Swing tilt (focal)",     "z_cond_fb * z_focal_tilt")
fe_reg("[7] Take rate (prior) x Attack angle (focal)",      "z_cond_take * z_focal_aa")

fe_reg("[8] Combined model: ss*aa + ld*tilt + chase*ad + swstr*ad",
       "z_cond_ss * z_focal_aa + z_cond_ld * z_focal_tilt + z_cond_chase * z_focal_ad + z_cond_swstr * z_focal_ad")

df_hi <- df %>% filter(num_pas > 50)
fe_reg("[9] Combined model, num_pas > 50",
       "z_cond_ss * z_focal_aa + z_cond_ld * z_focal_tilt + z_cond_chase * z_focal_ad + z_cond_swstr * z_focal_ad",
       data = df_hi)

# -----------------------------------------------------------------------------
# New ideas (2026-08-24): uses conditional_stats_with_baselines.csv, which adds
# nitro_x/nitro_z/nitro_dist (Euclidean distance between focal's and
# conditional's season-long barrel "nitro zone" locations) on top of the
# original conditional_lineup_stats_2025.csv columns.
# -----------------------------------------------------------------------------

fe_reg("[10] SwStr% (focal) x Swing path tilt (conditional)", "z_focal_swstr * z_cond_tilt")
fe_reg("[11] Swing% (focal) x Nitro zone distance",           "z_focal_swing * z_nitro_dist")
fe_reg("[12] Chase% (focal) x Attack angle (conditional)",    "z_focal_chase * z_cond_aa")
fe_reg("[13] Swing path tilt (focal) x Attack angle (conditional)", "z_focal_tilt * z_cond_aa")
fe_reg("[14] Chase% (focal) x Nitro zone distance",           "z_focal_chase * z_nitro_dist")

df_hi2 <- df %>% filter(num_pas > 50)
fe_reg("[10r] SwStr% (focal) x Swing path tilt (conditional), num_pas > 50", "z_focal_swstr * z_cond_tilt", data = df_hi2)
fe_reg("[11r] Swing% (focal) x Nitro zone distance, num_pas > 50",           "z_focal_swing * z_nitro_dist", data = df_hi2)
fe_reg("[12r] Chase% (focal) x Attack angle (conditional), num_pas > 50",    "z_focal_chase * z_cond_aa", data = df_hi2)
fe_reg("[13r] Swing path tilt (focal) x Attack angle (conditional), num_pas > 50", "z_focal_tilt * z_cond_aa", data = df_hi2)
fe_reg("[14r] Chase% (focal) x Nitro zone distance, num_pas > 50",           "z_focal_chase * z_nitro_dist", data = df_hi2)

# -----------------------------------------------------------------------------
# Simple single-variable regression: does nitro zone distance alone (no
# interaction, no fixed effects) predict focal run value?
# -----------------------------------------------------------------------------
hr("[15] focal_delta_run_exp_pa ~ nitro_dist (full sample, unweighted, no FE)",
   lm(focal_delta_run_exp_pa ~ nitro_dist, data = df))

hr("[15r] focal_delta_run_exp_pa ~ nitro_dist, num_pas > 50 (unweighted, no FE)",
   lm(focal_delta_run_exp_pa ~ nitro_dist, data = df_hi2))

# -----------------------------------------------------------------------------
# Nitro zone axis-by-axis (rather than collapsed to nitro_dist): does the
# conditional hitter's nitro-zone coordinate interact with the focal hitter's
# own coordinate on the same axis?
# -----------------------------------------------------------------------------
fe_reg("[16] Conditional nitro_x x Focal nitro_x", "z_cond_nitro_x * z_focal_nitro_x")
fe_reg("[17] Conditional nitro_z x Focal nitro_z", "z_cond_nitro_z * z_focal_nitro_z")

fe_reg("[16r] Conditional nitro_x x Focal nitro_x, num_pas > 50", "z_cond_nitro_x * z_focal_nitro_x", data = df_hi2)
fe_reg("[17r] Conditional nitro_z x Focal nitro_z, num_pas > 50", "z_cond_nitro_z * z_focal_nitro_z", data = df_hi2)

# Cross-axis: does one player's horizontal hot-zone location interact with the
# other's vertical hot-zone location?
fe_reg("[18] Conditional nitro_x x Focal nitro_z", "z_cond_nitro_x * z_focal_nitro_z")
fe_reg("[19] Conditional nitro_z x Focal nitro_x", "z_cond_nitro_z * z_focal_nitro_x")

fe_reg("[18r] Conditional nitro_x x Focal nitro_z, num_pas > 50", "z_cond_nitro_x * z_focal_nitro_z", data = df_hi2)
fe_reg("[19r] Conditional nitro_z x Focal nitro_x, num_pas > 50", "z_cond_nitro_z * z_focal_nitro_x", data = df_hi2)

# Conditional OBP x nitro zone distance (nitro_dist is a pair-level distance,
# not specific to either player)
fe_reg("[20] Conditional OBP x Nitro zone distance", "z_cond_obp * z_nitro_dist")
fe_reg("[20r] Conditional OBP x Nitro zone distance, num_pas > 50", "z_cond_obp * z_nitro_dist", data = df_hi2)

# -----------------------------------------------------------------------------
# Follow-up ideas (2026-08-24): 1, 2, 4, 5 from the suggested-regressions list
# -----------------------------------------------------------------------------

fe_reg("[21] Focal SLG x Nitro zone distance",                 "z_focal_slg * z_nitro_dist")
fe_reg("[22] Conditional SLG x Focal SweetSpot%",               "z_cond_slg * z_focal_ss")
fe_reg("[23] Focal GroundBall% x Conditional Attack angle",     "z_focal_gb * z_cond_aa")
fe_reg("[24] Focal FlyBall% x Conditional Swing path tilt",     "z_focal_fb * z_cond_tilt")

fe_reg("[21r] Focal SLG x Nitro zone distance, num_pas > 50",             "z_focal_slg * z_nitro_dist", data = df_hi2)
fe_reg("[22r] Conditional SLG x Focal SweetSpot%, num_pas > 50",           "z_cond_slg * z_focal_ss", data = df_hi2)
fe_reg("[23r] Focal GroundBall% x Conditional Attack angle, num_pas > 50", "z_focal_gb * z_cond_aa", data = df_hi2)
fe_reg("[24r] Focal FlyBall% x Conditional Swing path tilt, num_pas > 50", "z_focal_fb * z_cond_tilt", data = df_hi2)

fe_reg("[25] Conditional Contact% x Nitro zone distance",             "z_cond_contact * z_nitro_dist")
fe_reg("[25r] Conditional Contact% x Nitro zone distance, num_pas > 50", "z_cond_contact * z_nitro_dist", data = df_hi2)

fe_reg("[26] |Contact% gap| x Nitro zone distance",             "z_abs_contact_gap * z_nitro_dist")
fe_reg("[26r] |Contact% gap| x Nitro zone distance, num_pas > 50", "z_abs_contact_gap * z_nitro_dist", data = df_hi2)

fe_reg("[27] Conditional SwStr% x Nitro zone distance",             "z_cond_swstr * z_nitro_dist")
fe_reg("[27r] Conditional SwStr% x Nitro zone distance, num_pas > 50", "z_cond_swstr * z_nitro_dist", data = df_hi2)

# -----------------------------------------------------------------------------
# Sweep: every remaining season-level trait x nitro_dist, not yet tested.
# Extracts just the interaction term's p-value (full sample + num_pas > 50)
# into a summary table instead of printing full regression output for each.
# -----------------------------------------------------------------------------
remaining_vars <- c(
  "z_cond_ss", "z_cond_aa", "z_cond_ad", "z_cond_tilt", "z_cond_gb", "z_cond_fb",
  "z_cond_ld", "z_cond_pu", "z_cond_chase", "z_cond_take", "z_cond_slg",
  "z_focal_ss", "z_focal_aa", "z_focal_ad", "z_focal_tilt", "z_focal_gb",
  "z_focal_fb", "z_focal_ld", "z_focal_pu", "z_focal_swstr"
)

interaction_p <- function(var, data) {
  fml <- as.formula(paste0("focal_delta_run_exp_pa ~ ", var, " * z_nitro_dist",
                            " | focal_batter_id + conditional_batter_id"))
  m <- feols(fml, data = data, weights = ~num_pas, cluster = ~focal_batter_id)
  ct <- coeftable(m)
  int_row <- grep(":", rownames(ct), value = TRUE)
  if (length(int_row) == 0) return(c(estimate = NA, p = NA))
  c(estimate = ct[int_row, "Estimate"], p = ct[int_row, "Pr(>|t|)"])
}

sweep_results <- lapply(remaining_vars, function(v) {
  full_res <- tryCatch(interaction_p(v, df), error = function(e) c(estimate = NA, p = NA))
  hi_res   <- tryCatch(interaction_p(v, df_hi2), error = function(e) c(estimate = NA, p = NA))
  data.frame(
    variable = v,
    full_estimate = full_res["estimate"], full_p = full_res["p"],
    hi_estimate = hi_res["estimate"], hi_p = hi_res["p"]
  )
})
sweep_df <- do.call(rbind, sweep_results)
sweep_df$full_sig <- sweep_df$full_p < 0.05
sweep_df$hi_sig <- sweep_df$hi_p < 0.05

cat("\n==============================\n Sweep: remaining traits x nitro_dist \n==============================\n")
print(sweep_df, digits = 4, row.names = FALSE)

# Full detail on the sweep's significant hits (num_pas > 50)
fe_reg("[28] Conditional Attack Direction x Nitro zone distance", "z_cond_ad * z_nitro_dist")
fe_reg("[28r] Conditional Attack Direction x Nitro zone distance, num_pas > 50", "z_cond_ad * z_nitro_dist", data = df_hi2)

fe_reg("[29] Conditional GroundBall% x Nitro zone distance", "z_cond_gb * z_nitro_dist")
fe_reg("[29r] Conditional GroundBall% x Nitro zone distance, num_pas > 50", "z_cond_gb * z_nitro_dist", data = df_hi2)

fe_reg("[30] Conditional PopUp% x Nitro zone distance", "z_cond_pu * z_nitro_dist")
fe_reg("[30r] Conditional PopUp% x Nitro zone distance, num_pas > 50", "z_cond_pu * z_nitro_dist", data = df_hi2)

fe_reg("[31] Conditional Take% x Nitro zone distance", "z_cond_take * z_nitro_dist")
fe_reg("[31r] Conditional Take% x Nitro zone distance, num_pas > 50", "z_cond_take * z_nitro_dist", data = df_hi2)

# Robustness check on the standout result: does Conditional Attack Direction x
# nitro_dist hold up at different PA cutoffs, not just num_pas > 50?
df_hi40 <- df %>% filter(num_pas > 40)
df_hi75 <- df %>% filter(num_pas > 75)
fe_reg("[28-40] Conditional Attack Direction x Nitro zone distance, num_pas > 40", "z_cond_ad * z_nitro_dist", data = df_hi40)
fe_reg("[28-75] Conditional Attack Direction x Nitro zone distance, num_pas > 75", "z_cond_ad * z_nitro_dist", data = df_hi75)

# Same PA-cutoff robustness sweep for the other tier 3/4 findings
fe_reg("[21-40] Focal SLG x Nitro zone distance, num_pas > 40", "z_focal_slg * z_nitro_dist", data = df_hi40)
fe_reg("[21-75] Focal SLG x Nitro zone distance, num_pas > 75", "z_focal_slg * z_nitro_dist", data = df_hi75)

fe_reg("[13-40] Focal swing tilt x Conditional attack angle, num_pas > 40", "z_focal_tilt * z_cond_aa", data = df_hi40)
fe_reg("[13-75] Focal swing tilt x Conditional attack angle, num_pas > 75", "z_focal_tilt * z_cond_aa", data = df_hi75)

fe_reg("[27-40] Conditional SwStr% x Nitro zone distance, num_pas > 40", "z_cond_swstr * z_nitro_dist", data = df_hi40)
fe_reg("[27-75] Conditional SwStr% x Nitro zone distance, num_pas > 75", "z_cond_swstr * z_nitro_dist", data = df_hi75)

fe_reg("[29-40] Conditional GroundBall% x Nitro zone distance, num_pas > 40", "z_cond_gb * z_nitro_dist", data = df_hi40)
fe_reg("[29-75] Conditional GroundBall% x Nitro zone distance, num_pas > 75", "z_cond_gb * z_nitro_dist", data = df_hi75)

fe_reg("[30-40] Conditional PopUp% x Nitro zone distance, num_pas > 40", "z_cond_pu * z_nitro_dist", data = df_hi40)
fe_reg("[30-75] Conditional PopUp% x Nitro zone distance, num_pas > 75", "z_cond_pu * z_nitro_dist", data = df_hi75)

fe_reg("[31-40] Conditional Take% x Nitro zone distance, num_pas > 40", "z_cond_take * z_nitro_dist", data = df_hi40)
fe_reg("[31-75] Conditional Take% x Nitro zone distance, num_pas > 75", "z_cond_take * z_nitro_dist", data = df_hi75)
