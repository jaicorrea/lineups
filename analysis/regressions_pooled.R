# Pooled two-season (2024 + 2025) regressions.
# Motivation: ~2x the pairs gives the previously-underpowered checks
# (split-half, high-PA cutoffs, generalization) real teeth. Adds a season
# fixed effect on top of focal + conditional batter FE.

library(readr)
library(dplyr)
library(fixest)

df <- read_csv("../conditional_stats_with_baselines_pooled.csv", show_col_types = FALSE)
names(df) <- tolower(names(df))

zscore <- function(x) as.numeric(scale(x))

df <- df %>%
  mutate(
    contact_gap       = focal_season_contact_pct - conditional_season_contact_pct,
    swing_gap         = focal_season_swing_pct - conditional_season_swing_pct,
    chase_gap         = focal_season_chase_pct - conditional_season_chase_pct,
    swstr_gap         = focal_season_swstr_pct - conditional_season_swstr_pct,
    z_abs_contact_gap = zscore(abs(contact_gap)),
    z_abs_swing_gap   = zscore(abs(swing_gap)),
    z_abs_chase_gap   = zscore(abs(chase_gap)),
    z_abs_swstr_gap   = zscore(abs(swstr_gap)),
    z_contact_gap     = zscore(contact_gap),           # signed
    z_focal_slg       = zscore(focal_season_slg),
    z_cond_ad         = zscore(conditional_season_attack_direction_median),
    z_nitro_dist      = zscore(nitro_dist)
  )

hr <- function(label, model) {
  cat("\n==============================\n", label, "\n==============================\n")
  print(summary(model))
}

# Pooled FE: focal + conditional batter identity + season.
fe_reg <- function(label, rhs, data = df) {
  fml <- as.formula(paste0("focal_delta_run_exp_pa ~ ", rhs,
                            " | focal_batter_id + conditional_batter_id + season"))
  hr(label, feols(fml, data = data, weights = ~num_pas, cluster = ~focal_batter_id))
}

df_hi  <- df %>% filter(num_pas > 50)
df_hi40 <- df %>% filter(num_pas > 40)
df_hi75 <- df %>% filter(num_pas > 75)

cat("\n#### N by sample ####\n")
cat("full:", nrow(df), " >40:", nrow(df_hi40), " >50:", nrow(df_hi), " >75:", nrow(df_hi75), "\n")

# =====================================================================
# 1) The durable finding: |contact gap| x focal SLG, across cutoffs
# =====================================================================
fe_reg("[P1] |contact gap| x SLG (full)",   "z_abs_contact_gap * z_focal_slg")
fe_reg("[P1-50] |contact gap| x SLG, >50",  "z_abs_contact_gap * z_focal_slg", data = df_hi)
fe_reg("[P1-40] |contact gap| x SLG, >40",  "z_abs_contact_gap * z_focal_slg", data = df_hi40)
fe_reg("[P1-75] |contact gap| x SLG, >75",  "z_abs_contact_gap * z_focal_slg", data = df_hi75)

# Split-half (now each half ~1,200 obs -- the check that was underpowered before)
set.seed(20260824)
df_sh <- df %>% mutate(.half = sample(rep(c(1L, 2L), length.out = n())))
fe_reg("[P1-h1] |contact gap| x SLG, split-half #1", "z_abs_contact_gap * z_focal_slg",
       data = df_sh %>% filter(.half == 1))
fe_reg("[P1-h2] |contact gap| x SLG, split-half #2", "z_abs_contact_gap * z_focal_slg",
       data = df_sh %>% filter(.half == 2))

# =====================================================================
# 2) Generalization: does the amplification hold for OTHER style gaps?
# =====================================================================
fe_reg("[P2-signed] signed contact gap x SLG (full)", "z_contact_gap * z_focal_slg")
fe_reg("[P2-swing]  |swing gap| x SLG (full)",  "z_abs_swing_gap * z_focal_slg")
fe_reg("[P2-chase]  |chase gap| x SLG (full)",  "z_abs_chase_gap * z_focal_slg")
fe_reg("[P2-swstr]  |swstr gap| x SLG (full)",  "z_abs_swstr_gap * z_focal_slg")

# =====================================================================
# 3) The other candidate: Conditional Attack Direction x nitro_dist
# =====================================================================
fe_reg("[P3] cond attack dir x nitro_dist (full)",  "z_cond_ad * z_nitro_dist")
fe_reg("[P3-50] cond attack dir x nitro_dist, >50", "z_cond_ad * z_nitro_dist", data = df_hi)
fe_reg("[P3-40] cond attack dir x nitro_dist, >40", "z_cond_ad * z_nitro_dist", data = df_hi40)
fe_reg("[P3-75] cond attack dir x nitro_dist, >75", "z_cond_ad * z_nitro_dist", data = df_hi75)
