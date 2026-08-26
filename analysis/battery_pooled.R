# Full complementarity battery, run on POOLED 2024+2025 data.
# Every interaction spec tested this session, refit with focal+conditional+season
# FE, weighted by num_pas, clustered on focal_batter_id. Extracts each
# interaction term's p-value for the full sample and num_pas>50, into one table.

library(readr); library(dplyr); library(fixest)

df <- read_csv("../conditional_stats_with_baselines_pooled.csv", show_col_types = FALSE)
names(df) <- tolower(names(df))
z <- function(x) as.numeric(scale(x))

df <- df %>% mutate(
  cond_take_pct = 1 - conditional_season_swing_pct,
  same_side = ifelse(!is.na(focal_hitterside) & !is.na(conditional_hitterside),
                     as.numeric(focal_hitterside == conditional_hitterside), NA),
  opp_side  = ifelse(!is.na(same_side), 1 - same_side, NA),
  # conditional-side z-vars
  z_cond_obp=z(conditional_season_obp), z_cond_take=z(cond_take_pct),
  z_cond_contact=z(conditional_season_contact_pct), z_cond_barrel=z(conditional_season_barrel_pa),
  z_cond_slg=z(conditional_season_slg), z_cond_ss=z(conditional_season_sweetspot_pct),
  z_cond_aa=z(conditional_season_attack_angle_median), z_cond_ad=z(conditional_season_attack_direction_median),
  z_cond_tilt=z(conditional_season_swing_path_tilt_median), z_cond_gb=z(conditional_season_groundball_pct),
  z_cond_fb=z(conditional_season_flyball_pct), z_cond_ld=z(conditional_season_linedrive_pct),
  z_cond_pu=z(conditional_season_popup_pct), z_cond_chase=z(conditional_season_chase_pct),
  z_cond_swstr=z(conditional_season_swstr_pct),
  # focal-side z-vars
  z_focal_slg=z(focal_season_slg), z_focal_barrel=z(focal_season_barrel_pa),
  z_focal_ss=z(focal_season_sweetspot_pct), z_focal_aa=z(focal_season_attack_angle_median),
  z_focal_ad=z(focal_season_attack_direction_median), z_focal_tilt=z(focal_season_swing_path_tilt_median),
  z_focal_gb=z(focal_season_groundball_pct), z_focal_fb=z(focal_season_flyball_pct),
  z_focal_swing=z(focal_season_swing_pct), z_focal_chase=z(focal_season_chase_pct),
  z_focal_swstr=z(focal_season_swstr_pct),
  # gaps
  z_abs_swing_gap=z(abs(focal_season_swing_pct-conditional_season_swing_pct)),
  z_abs_contact_gap=z(abs(focal_season_contact_pct-conditional_season_contact_pct)),
  z_abs_chase_gap=z(abs(focal_season_chase_pct-conditional_season_chase_pct)),
  z_abs_swstr_gap=z(abs(focal_season_swstr_pct-conditional_season_swstr_pct)),
  z_contact_gap=z(focal_season_contact_pct-conditional_season_contact_pct),
  z_nitro_dist=z(nitro_dist)
)
df_hi <- df %>% filter(num_pas > 50)

# spec list: label -> rhs (interaction form). Interaction term p-value extracted.
specs <- list(
  # OBP/SLG complementarity family
  "cond_obp x focal_slg"        = "z_cond_obp * z_focal_slg",
  "cond_take x focal_slg"       = "z_cond_take * z_focal_slg",
  "cond_contact x focal_slg"    = "z_cond_contact * z_focal_slg",
  "cond_barrel x focal_slg"     = "z_cond_barrel * z_focal_slg",
  "cond_obp x focal_barrel"     = "z_cond_obp * z_focal_barrel",
  "|swing gap| x focal_slg"     = "z_abs_swing_gap * z_focal_slg",
  "|contact gap| x focal_slg"   = "z_abs_contact_gap * z_focal_slg",
  "|chase gap| x focal_slg"     = "z_abs_chase_gap * z_focal_slg",
  "|swstr gap| x focal_slg"     = "z_abs_swstr_gap * z_focal_slg",
  "signed contact gap x slg"    = "z_contact_gap * z_focal_slg",
  # swing-mechanics family
  "cond_ss x focal_aa"          = "z_cond_ss * z_focal_aa",
  "cond_ld x focal_tilt"        = "z_cond_ld * z_focal_tilt",
  "cond_chase x focal_ad"       = "z_cond_chase * z_focal_ad",
  "cond_swstr x focal_ad"       = "z_cond_swstr * z_focal_ad",
  "cond_gb x focal_aa"          = "z_cond_gb * z_focal_aa",
  "cond_fb x focal_tilt"        = "z_cond_fb * z_focal_tilt",
  "cond_take x focal_aa"        = "z_cond_take * z_focal_aa",
  "focal_swstr x cond_tilt"     = "z_focal_swstr * z_cond_tilt",
  "focal_chase x cond_aa"       = "z_focal_chase * z_cond_aa",
  "focal_tilt x cond_aa"        = "z_focal_tilt * z_cond_aa",
  "cond_slg x focal_ss"         = "z_cond_slg * z_focal_ss",
  "focal_gb x cond_aa"          = "z_focal_gb * z_cond_aa",
  "focal_fb x cond_tilt"        = "z_focal_fb * z_cond_tilt",
  # nitro_dist family
  "focal_slg x nitro_dist"      = "z_focal_slg * z_nitro_dist",
  "cond_obp x nitro_dist"       = "z_cond_obp * z_nitro_dist",
  "cond_ad x nitro_dist"        = "z_cond_ad * z_nitro_dist",
  "cond_take x nitro_dist"      = "z_cond_take * z_nitro_dist",
  "cond_gb x nitro_dist"        = "z_cond_gb * z_nitro_dist",
  "cond_pu x nitro_dist"        = "z_cond_pu * z_nitro_dist",
  "cond_swstr x nitro_dist"     = "z_cond_swstr * z_nitro_dist",
  "cond_contact x nitro_dist"   = "z_cond_contact * z_nitro_dist",
  "focal_swing x nitro_dist"    = "z_focal_swing * z_nitro_dist",
  "focal_chase x nitro_dist"    = "z_focal_chase * z_nitro_dist",
  "|contact gap| x nitro_dist"  = "z_abs_contact_gap * z_nitro_dist"
)

int_p <- function(rhs, data) {
  fml <- as.formula(paste0("focal_delta_run_exp_pa ~ ", rhs,
                           " | focal_batter_id + conditional_batter_id + season"))
  m <- tryCatch(feols(fml, data = data, weights = ~num_pas, cluster = ~focal_batter_id),
                error = function(e) NULL)
  if (is.null(m)) return(c(est = NA, p = NA))
  ct <- coeftable(m); ir <- grep(":", rownames(ct), value = TRUE)
  if (length(ir) == 0) return(c(est = NA, p = NA))
  c(est = ct[ir[1], "Estimate"], p = ct[ir[1], "Pr(>|t|)"])
}

rows <- lapply(names(specs), function(lab) {
  f <- int_p(specs[[lab]], df); h <- int_p(specs[[lab]], df_hi)
  data.frame(spec = lab, full_est = f["est"], full_p = f["p"],
             hi_est = h["est"], hi_p = h["p"])
})
res <- do.call(rbind, rows)
res$full_sig <- ifelse(!is.na(res$full_p) & res$full_p < 0.05, "*", "")
res$hi_sig   <- ifelse(!is.na(res$hi_p)   & res$hi_p   < 0.05, "*", "")
res <- res[order(res$hi_p), ]

cat("\n=== POOLED 2024+2025 FULL BATTERY (n_full=", nrow(df),
    ", n>50=", nrow(df_hi), ") ===\n", sep = "")
cat("Interaction-term p-values; FE = focal+conditional+season; * = p<0.05\n")
cat("Bonferroni threshold across", length(specs), "specs: p <",
    round(0.05/length(specs), 5), "\n\n")
print(res, digits = 3, row.names = FALSE)
