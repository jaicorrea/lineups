# The 11 pre-specified predecessor x focal interactions (final analysis).
#
# Every spec: outcome ~ z_cond_X * z_focal_Y | focal_batter_id^season + conditional_batter_id^season
# traits z-scored within season, weights = num_pas, SEs clustered on the focal hitter
# (team-season clustering also reported). Holm correction is applied to the 11 tests per outcome.
# Outcomes: Barrel/PA (primary) and run value per PA (secondary).
#
# Usage (from analysis/):  Rscript all11.R [path_to_pooled_csv] [focal|cond]
# Writes all11_pooled.csv and all11_by_season.csv to the working directory.
# With the "cond" argument the outcome is the predecessor's run value per PA
# (conditional_delta_run_exp_pa) and the files are all11_cond_pooled.csv / all11_cond_by_season.csv.
library(readr); library(dplyr); library(fixest)
fixest::setFixest_nthreads(1)   # multithreaded fixest crashes on this data on Windows

args <- commandArgs(trailingOnly = TRUE)
path <- if (length(args) >= 1) args[1] else "../data/pooled/conditional_stats_with_baselines_pooled_all_team.csv"
MODE <- if (length(args) >= 2) args[2] else "focal"   # "focal" (default) or "cond"
df <- read_csv(path, show_col_types = FALSE)
names(df) <- tolower(names(df))
z <- function(x) as.numeric(scale(x))

# trait key -> column stem (prefixed with focal_season_ / conditional_season_)
stem <- c(
  swing = "swing_pct", swstr = "swstr_pct", chase = "chase_pct", contact = "contact_pct",
  aa = "attack_angle_median", ad = "attack_direction_median", tilt = "swing_path_tilt_median",
  ss = "sweetspot_pct", ld = "linedrive_pct", nz = "nitro_z", barrel = "barrel_pa", pitchpa = "pitch_pa"
)
for (k in names(stem)) {
  df[[paste0("raw_cond_", k)]]  <- df[[paste0("conditional_season_", stem[k])]]
  df[[paste0("raw_focal_", k)]] <- df[[paste0("focal_season_", stem[k])]]
}
df <- df %>%
  group_by(season) %>%
  mutate(across(starts_with("raw_"), z, .names = "z_{sub('raw_', '', .col)}")) %>%
  ungroup()
df$ts <- paste(df$team, df$season)

FE_PXS <- "focal_batter_id^season + conditional_batter_id^season"
FE_ONE <- "focal_batter_id + conditional_batter_id"
cat("rows:", nrow(df), "| rows by season:", paste(names(table(df$season)), table(df$season), collapse = "; "),
    "| min pair PA:", min(df$num_pas), "\n")

specs <- data.frame(
  spec = c("cond_ss x focal_aa","cond_ld x focal_tilt","cond_chase x focal_ad","cond_tilt x focal_swstr","cond_nz x focal_ad",
           "cond_aa x focal_chase","cond_aa x focal_tilt","cond_contact x focal_barrel","cond_chase x focal_swing",
           "cond_pitchpa x focal_tilt","cond_tilt x focal_pitchpa"),
  rhs = c("z_cond_ss * z_focal_aa","z_cond_ld * z_focal_tilt","z_cond_chase * z_focal_ad","z_cond_tilt * z_focal_swstr","z_cond_nz * z_focal_ad",
          "z_cond_aa * z_focal_chase","z_cond_aa * z_focal_tilt","z_cond_contact * z_focal_barrel","z_cond_chase * z_focal_swing",
          "z_cond_pitchpa * z_focal_tilt","z_cond_tilt * z_focal_pitchpa"), stringsAsFactors = FALSE)
if (MODE == "cond") {
  # Reverse direction: the predecessor's own run value per PA, in the PAs where this focal hitter
  # batted right behind him (does the hitter behind change how the predecessor performs?)
  dvs <- c(cond_runval = "conditional_delta_run_exp_pa")
} else {
  dvs <- c(barrel = "focal_barrel_pa", runval = "focal_delta_run_exp_pa")
}

fit <- function(dv, rhs, dat, fe, cl) {
  vv <- c(dv, all.vars(as.formula(paste("~", rhs))), "num_pas", "focal_batter_id", "conditional_batter_id", "ts", "season")
  dat <- dat[complete.cases(dat[, vv]), ]   # complete cases: NAs crash fixest under team clustering
  m <- tryCatch(suppressMessages(suppressWarnings(feols(as.formula(paste0(dv, " ~ ", rhs, " | ", fe)),
         data = dat, weights = ~num_pas, cluster = cl, notes = FALSE))), error = function(e) NULL)
  if (is.null(m)) return(c(est = NA, se = NA, p = NA, n = NA))
  ct <- coeftable(m); ir <- grep(":", rownames(ct))[1]
  c(est = ct[ir, 1], se = ct[ir, 2], p = ct[ir, 4], n = nobs(m))
}
cls <- list(focal = ~focal_batter_id, team = ~ts, twoway = ~focal_batter_id + conditional_batter_id)
options(width = 220)

A <- do.call(rbind, lapply(names(dvs), function(o) {
  r <- do.call(rbind, lapply(seq_len(nrow(specs)), function(k) {
    f <- lapply(cls, function(cl) fit(dvs[[o]], specs$rhs[k], df, FE_PXS, cl))
    data.frame(outcome = o, spec = specs$spec[k], used = f$focal["n"], est = f$focal["est"], se = f$focal["se"],
               p_focal = f$focal["p"], p_team = f$team["p"], p_twoway = f$twoway["p"],
               se_ratio_team = f$team["se"] / f$focal["se"], row.names = NULL)
  }))
  r$holm11 <- p.adjust(r$p_focal, "holm"); r$holm11_team <- p.adjust(r$p_team, "holm"); r
}))
cat("\n== POOLED, all pairs, player x season FE, PA weights, Holm over 11 tests ==\n")
print(A %>% mutate(est = signif(est, 3), se = signif(se, 3),
                   across(c(p_focal, p_team, p_twoway, holm11, holm11_team), ~round(., 3)),
                   se_ratio_team = round(se_ratio_team, 2)), row.names = FALSE)

B <- do.call(rbind, lapply(names(dvs), function(o) do.call(rbind, lapply(seq_len(nrow(specs)), function(k)
  do.call(rbind, lapply(sort(unique(df$season)), function(s) {
    f <- fit(dvs[[o]], specs$rhs[k], df %>% filter(season == s), FE_ONE, ~focal_batter_id)
    data.frame(outcome = o, spec = specs$spec[k], season = s, est = f["est"], p = f["p"], n = f["n"], row.names = NULL) }))))))
cat("\n== BY SEASON (within-season FE), focal-clustered p ==\n")
print(reshape(B %>% mutate(est = signif(est, 2), p = round(p, 3)) %>% select(-n),
              idvar = c("outcome", "spec"), timevar = "season", direction = "wide"), row.names = FALSE)

sfx <- if (MODE == "cond") "_cond" else ""
write.csv(A, paste0("all11", sfx, "_pooled.csv"), row.names = FALSE)
write.csv(B, paste0("all11", sfx, "_by_season.csv"), row.names = FALSE)
