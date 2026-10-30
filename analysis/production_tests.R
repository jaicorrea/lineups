# Post hoc production-trait interactions (predecessor x focal), same design as all11.R.
#
# Five pairings of the predecessor's and focal hitter's production traits:
#   cond OBP x focal SLG, cond Barrel/PA x focal BB%, cond K% x focal BB%,
#   cond K-BB% x focal Barrel/PA, cond OBP x focal BA.
# These were run AFTER the eleven pre-specified tests, so they are exploratory; Holm is over these 5 per outcome.
# Outcomes: focal Barrel/PA, focal run value/PA, and the predecessor's run value/PA (reverse direction).
# BB%, K%, K-BB% come from analysis/kbb_traits.csv (data code/build_kbb_traits.py).
#
# Usage (from analysis/):  Rscript production_tests.R [path_to_pooled_csv]
# Writes production_pooled.csv and production_by_season.csv to the working directory.
library(readr); library(dplyr); library(fixest)
fixest::setFixest_nthreads(1)

args <- commandArgs(trailingOnly = TRUE)
path <- if (length(args) >= 1) args[1] else "../data/pooled/conditional_stats_with_baselines_pooled_all_team.csv"
df <- read_csv(path, show_col_types = FALSE)
names(df) <- tolower(names(df))
z <- function(x) as.numeric(scale(x))

kbb <- read_csv("kbb_traits.csv", show_col_types = FALSE)
names(kbb) <- tolower(names(kbb))
kbb <- kbb %>% select(season, batter, stand, bb_pct, k_pct, kbb_pct)
df <- df %>%
  left_join(kbb %>% rename(focal_batter_id = batter, focal_hitterside = stand,
                           f_bb = bb_pct, f_k = k_pct, f_kbb = kbb_pct),
            by = c("season", "focal_batter_id", "focal_hitterside")) %>%
  left_join(kbb %>% rename(conditional_batter_id = batter, conditional_hitterside = stand,
                           c_bb = bb_pct, c_k = k_pct, c_kbb = kbb_pct),
            by = c("season", "conditional_batter_id", "conditional_hitterside"))
cat("unmatched BB/K traits: focal", sum(is.na(df$f_bb)), "| cond", sum(is.na(df$c_bb)), "of", nrow(df), "\n")

raw <- list(
  cond_obp = "conditional_season_obp", cond_barrel = "conditional_season_barrel_pa",
  cond_k = "c_k", cond_kbb = "c_kbb",
  focal_slg = "focal_season_slg", focal_ba = "focal_season_ba", focal_bb = "f_bb", focal_barrel = "focal_season_barrel_pa")
for (k in names(raw)) df[[paste0("raw_", k)]] <- df[[raw[[k]]]]
df <- df %>%
  group_by(season) %>%
  mutate(across(starts_with("raw_"), z, .names = "z_{sub('raw_', '', .col)}")) %>%
  ungroup()
df$ts <- paste(df$team, df$season)

FE_PXS <- "focal_batter_id^season + conditional_batter_id^season"
FE_ONE <- "focal_batter_id + conditional_batter_id"

specs <- data.frame(
  spec = c("cond_obp x focal_slg", "cond_barrel x focal_bb", "cond_k x focal_bb", "cond_kbb x focal_barrel", "cond_obp x focal_ba"),
  rhs  = c("z_cond_obp * z_focal_slg", "z_cond_barrel * z_focal_bb", "z_cond_k * z_focal_bb",
           "z_cond_kbb * z_focal_barrel", "z_cond_obp * z_focal_ba"), stringsAsFactors = FALSE)
dvs <- c(barrel = "focal_barrel_pa", runval = "focal_delta_run_exp_pa", cond_runval = "conditional_delta_run_exp_pa")

fit <- function(dv, rhs, dat, fe, cl) {
  vv <- c(dv, all.vars(as.formula(paste("~", rhs))), "num_pas", "focal_batter_id", "conditional_batter_id", "ts", "season")
  dat <- dat[complete.cases(dat[, vv]), ]
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
               p_focal = f$focal["p"], p_team = f$team["p"], p_twoway = f$twoway["p"], row.names = NULL)
  }))
  r$holm5 <- p.adjust(r$p_focal, "holm"); r$holm5_team <- p.adjust(r$p_team, "holm"); r
}))
cat("\n== POOLED, player x season FE, PA weights, Holm over 5 tests per outcome ==\n")
print(A %>% mutate(est = signif(est, 3), se = signif(se, 3), across(c(p_focal, p_team, p_twoway, holm5, holm5_team), ~round(., 3))), row.names = FALSE)

B <- do.call(rbind, lapply(names(dvs), function(o) do.call(rbind, lapply(seq_len(nrow(specs)), function(k)
  do.call(rbind, lapply(sort(unique(df$season)), function(s) {
    f <- fit(dvs[[o]], specs$rhs[k], df %>% filter(season == s), FE_ONE, ~focal_batter_id)
    data.frame(outcome = o, spec = specs$spec[k], season = s, est = f["est"], p = f["p"], n = f["n"], row.names = NULL) }))))))
cat("\n== BY SEASON (within-season FE), focal-clustered p ==\n")
print(reshape(B %>% mutate(est = signif(est, 2), p = round(p, 3)) %>% select(-n),
              idvar = c("outcome", "spec"), timevar = "season", direction = "wide"), row.names = FALSE)

write.csv(A, "production_pooled.csv", row.names = FALSE)
write.csv(B, "production_by_season.csv", row.names = FALSE)
