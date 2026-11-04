# Table 1: the 12 pre-specified conditional x focal interactions (beta_3 on the product term).
#
# Every spec: outcome ~ z_cond_X * z_focal_Y | focal_batter_id^season + conditional_batter_id^season
# traits z-scored within season, weights = num_pas, SEs two-way clustered on the focal and conditional hitter.
# Two sets of 12: outcome = focal_delta_run_exp_pa, then outcome = conditional_delta_run_exp_pa.
#
# Usage (from analysis/):  Rscript table1_regressions.R [path_to_pooled_csv] [season|all]
# Default season is 2025 (hitter fixed effects); "all" pools 2025-2026 (hitter x season fixed effects).
# Writes table1_{focal,cond}_<2025|pooled>.tex and ..._results.csv to the working directory.
library(readr); library(dplyr); library(fixest)
fixest::setFixest_nthreads(1)   # multithreaded fixest crashes on this data on Windows

args <- commandArgs(trailingOnly = TRUE)
# The wOBA file is the pooled table plus pair wOBA/xwOBA, built by data code/build_woba_outcomes.py
path <- if (length(args) >= 1) args[1] else "../data/pooled/conditional_stats_with_woba_pooled_all_team.csv"
SEASON <- if (length(args) >= 2) args[2] else "2025"   # a single season, or "all" for the pooled robustness check
df <- read_csv(path, show_col_types = FALSE)
names(df) <- tolower(names(df))
if (SEASON != "all") df <- df %>% filter(season == as.integer(SEASON))
sfx <- if (SEASON == "all") "pooled" else SEASON
z <- function(x) as.numeric(scale(x))

# trait key -> column stem (prefixed with focal_season_ / conditional_season_)
stem <- c(
  obp = "obp", slg = "slg", swing = "swing_pct", swstr = "swstr_pct", chase = "chase_pct",
  contact = "contact_pct", aa = "attack_angle_median", ad = "attack_direction_median",
  tilt = "swing_path_tilt_median", ss = "sweetspot_pct", ld = "linedrive_pct",
  barrel = "barrel_pa", pitchpa = "pitch_pa"
)
for (k in names(stem)) {
  df[[paste0("raw_cond_", k)]]  <- df[[paste0("conditional_season_", stem[k])]]
  df[[paste0("raw_focal_", k)]] <- df[[paste0("focal_season_", stem[k])]]
}
# Pair-level traits
df$raw_gap  <- abs(df$focal_season_contact_pct - df$conditional_season_contact_pct)
df$raw_nzd  <- df$nitro_dist

df <- df %>%
  group_by(season) %>%
  mutate(across(starts_with("raw_"), z, .names = "z_{sub('raw_', '', .col)}")) %>%
  ungroup()

FE <- if (SEASON == "all") "focal_batter_id^season + conditional_batter_id^season" else "focal_batter_id + conditional_batter_id"
FE_TEX <- if (SEASON == "all") {
  "focal-hitter$\\times$season and conditional-hitter$\\times$season fixed effects, pooled across 2025--2026"
} else {
  paste0("focal-hitter and conditional-hitter fixed effects, ", SEASON, " season only")
}

# Table 1, in order: the interaction term is z_<conditional trait> * z_<focal trait>
specs <- data.frame(
  n = 1:12,
  cond = c("OBP", "Abs contact gap", "Sweet spot %", "Line-drive %", "Chase %", "Swing path tilt",
           "Nitro dist", "Attack angle", "Swing path tilt", "Contact %", "Chase %", "Pitch/PA"),
  focal = c("SLG", "SLG", "Attack angle", "Swing path tilt", "Attack direction", "Swinging-strike %",
            "Attack direction", "Chase %", "Attack angle", "Barrel/PA", "Swing %", "Swing path tilt"),
  rhs = c("z_cond_obp * z_focal_slg",
          "z_gap * z_focal_slg",
          "z_cond_ss * z_focal_aa",
          "z_cond_ld * z_focal_tilt",
          "z_cond_chase * z_focal_ad",
          "z_cond_tilt * z_focal_swstr",
          "z_nzd * z_focal_ad",
          "z_cond_aa * z_focal_chase",
          "z_cond_tilt * z_focal_aa",
          "z_cond_contact * z_focal_barrel",
          "z_cond_chase * z_focal_swing",
          "z_cond_pitchpa * z_focal_tilt"),
  expected = c("+", "+", "+", "+", "-", "-", "-", "-", "-", "+", "-", "+"),
  stringsAsFactors = FALSE
)

fit <- function(dv, rhs) {
  invisible(gc())   # native fixest crashes on Windows are less likely with a clean heap
  vv <- c(dv, all.vars(as.formula(paste("~", rhs))), "num_pas", "focal_batter_id", "conditional_batter_id", "season")
  dat <- df[complete.cases(df[, vv]), ]
  if (dv == "woba_pair") dat <- dat[dat$woba_pa_mismatch == 0, ]   # drop pairs whose PA count disagrees with num_pas
  m <- feols(as.formula(paste0(dv, " ~ ", rhs, " | ", FE)),
             data = dat, weights = ~num_pas, cluster = ~focal_batter_id + conditional_batter_id, notes = FALSE)
  ct <- coeftable(m); ir <- grep(":", rownames(ct))[1]
  c(est = ct[ir, 1], se = ct[ir, 2], p = ct[ir, 4], n = nobs(m))
}

run_set <- function(dv) {
  res <- do.call(rbind, lapply(seq_len(nrow(specs)), function(i) {
    f <- fit(dv, specs$rhs[i])
    data.frame(specs[i, c("n", "cond", "focal", "expected")], est = f["est"], se = f["se"],
               p = f["p"], nobs = f["n"], row.names = NULL)
  }))
  res$sign_match <- ifelse(sign(res$est) == ifelse(res$expected == "+", 1, -1), "yes", "no")
  res$holm <- p.adjust(res$p, "holm")
  res
}

tex_esc <- function(x) gsub("([%&])", "\\\\\\1", x)
stars <- function(p) ifelse(p < 0.01, "\\textsuperscript{***}", ifelse(p < 0.05, "\\textsuperscript{**}",
                     ifelse(p < 0.1, "\\textsuperscript{*}", "")))

# LaTeX table (booktabs) for one outcome; needs \usepackage{booktabs} in the preamble
write_tex <- function(res, file, caption, label) {
  rows <- sprintf("%d & %s & %s & %s & $%s$%s & (%s) & %.3f \\\\",
                  res$n, tex_esc(res$cond), tex_esc(res$focal),
                  ifelse(res$expected == "+", "$+$", "$-$"),
                  formatC(res$est, format = "f", digits = 4), stars(res$p),
                  formatC(res$se, format = "f", digits = 4), res$p)
  tex <- c("\\begin{table}[htbp]", "\\centering", "\\small",
           paste0("\\caption{", caption, "}"), paste0("\\label{", label, "}"),
           "\\begin{tabular}{clllccc}", "\\toprule",
           "No. & Conditional trait & Focal trait & Expected sign & $\\hat\\beta_3$ & SE & $p$-value \\\\",
           "\\midrule", rows, "\\bottomrule",
           "\\end{tabular}",
           paste0("\\par\\smallskip\\parbox{0.95\\textwidth}{\\footnotesize \\textit{Notes:} Each row is a separate regression of the outcome on the standardized conditional trait, the standardized focal trait and their interaction, with ", FE_TEX, ", weighted by plate appearances. Traits are z-scored within season. Standard errors, two-way clustered by focal hitter and conditional hitter, in parentheses. \\textsuperscript{*}$p<0.10$, \\textsuperscript{**}$p<0.05$, \\textsuperscript{***}$p<0.01$.}"),
           "\\end{table}")
  writeLines(tex, file)
}

options(width = 220)
sets <- list(
  focal = list(dv = "focal_delta_run_exp_pa",
               caption = "Interaction coefficient $\\beta_3$ on focal hitter's delta run expectancy",
               label = "tab:table1_focal"),
  cond  = list(dv = "conditional_delta_run_exp_pa",
               caption = "Interaction coefficient $\\beta_3$ on conditional hitter's delta run expectancy",
               label = "tab:table1_cond"),
  woba  = list(dv = "woba_pair",
               caption = "Interaction coefficient $\\beta_3$ on focal hitter's wOBA",
               label = "tab:table1_woba"),
  barrel = list(dv = "focal_barrel_pa",
               caption = "Interaction coefficient $\\beta_3$ on focal hitter's Barrel/PA",
               label = "tab:table1_barrel"))
for (nm in names(sets)) {
  s <- sets[[nm]]
  cat("\n== Outcome:", s$dv, "==\n")
  res <- run_set(s$dv)
  print(res %>% mutate(est = signif(est, 3), se = signif(se, 3), p = round(p, 3), holm = round(holm, 3)),
        row.names = FALSE)
  write.csv(res, paste0("table1_", nm, "_", sfx, "_results.csv"), row.names = FALSE)
  write_tex(res, paste0("table1_", nm, "_", sfx, ".tex"), s$caption, paste0(s$label, "_", sfx))
}
