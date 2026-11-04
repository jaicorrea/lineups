# Is Barrel/PA (or wOBA) a good proxy for run value per PA?
#
# One row per hitter-season (all hitters in the PA files, not only focal or conditional ones), 2025 by default.
# Barrel/PA, run value per PA (delta_run_exp) and wOBA are built from the PA-level Statcast files with the
# pipeline's own PA definition (events present, truncated_pa dropped); Barrel is launch_speed_angle == 6.
# wOBA = sum(woba_value) / sum(woba_denom). Regressions are weighted by PAs, SEs clustered on the hitter,
# on one common sample so the R2 of the two proxies is comparable.
#
# Usage (from the repo root or analysis/):  Rscript analysis/proxy_regressions.R
# Writes proxy_regressions.tex (LaTeX, needs booktabs) next to this script's working directory.
library(readr); library(dplyr); library(fixest)

root <- if (dir.exists("statcast hitters 2025")) "." else ".."
dirs <- c(`2025` = "statcast hitters 2025", `2026` = "statcast hitters 2026")
cols <- cols_only(batter = "i", events = "c", launch_speed_angle = "d", delta_run_exp = "d",
                  woba_value = "d", woba_denom = "d")
pa <- bind_rows(lapply(names(dirs), function(s) {
  fs <- list.files(file.path(root, dirs[[s]]), "\\.csv$", full.names = TRUE)
  bind_rows(lapply(fs, read_csv, col_types = cols, progress = FALSE)) %>% mutate(season = as.integer(s))
}))

# The PA files' woba_value is rounded (1B .9, BB .7, HR 2.0, ROE as a hit) and runs ~.012 above Savant, so wOBA
# is rebuilt from the event with unrounded linear weights (matches the Savant leaderboard within .002).
woba_w <- c(walk = 0.69, hit_by_pitch = 0.72, single = 0.88, double = 1.247, triple = 1.578, home_run = 2.031)
pa$woba_value <- ifelse(pa$events %in% names(woba_w), woba_w[pa$events], 0)

h <- pa %>%
  filter(!is.na(events), events != "truncated_pa") %>%
  group_by(batter, season) %>%
  summarise(pa = n(),
            barrel = sum(launch_speed_angle == 6, na.rm = TRUE) / n(),
            rv = mean(delta_run_exp, na.rm = TRUE),
            woba_den = sum(woba_denom, na.rm = TRUE),
            woba = sum(woba_value, na.rm = TRUE) / sum(woba_denom, na.rm = TRUE),
            .groups = "drop") %>%
  filter(woba_den > 0) %>%
  mutate(barrel_pp = barrel * 100, woba_pts = woba * 1000)   # per percentage point / per wOBA point

# Usage: Rscript analysis/proxy_regressions.R [all]   (default 2025 only; "all" pools 2025-2026)
args <- commandArgs(trailingOnly = TRUE)
POOLED <- length(args) >= 1 && args[1] == "all"
if (!POOLED) h <- h %>% filter(season == 2025)
sample_lbl <- if (POOLED) "2025--2026" else "2025"

cat("hitter-seasons:", nrow(h), "| corr(rv, barrel):", round(cor(h$rv, h$barrel), 3),
    "| corr(rv, woba):", round(cor(h$rv, h$woba), 3), "
")

# Two separate single regressions of run value per PA, on one common sample
m <- list(
  "Barrel/PA" = feols(rv ~ barrel_pp, h, weights = ~pa, cluster = ~batter),
  "wOBA"      = feols(rv ~ woba_pts,  h, weights = ~pa, cluster = ~batter)
)

options(width = 200)
etable(m, digits = 4, fitstat = ~ n + r2 + ar2)

etable(m, digits = 4, fitstat = ~ n + r2,
       dict = c(barrel_pp = "Barrel/PA (pct. points)", woba_pts = "wOBA (points)", rv = "$\\Delta$ Run Expectancy"),
       title = "Hitter-season $\\Delta$ run expectancy per PA on Barrel/PA and wOBA",
       notes = paste0(sample_lbl, " hitter-seasons, weighted by PAs; standard errors clustered by hitter in parentheses."),
       tex = TRUE, style.tex = style.tex("base"), file = if (POOLED) "proxy_regressions_pooled.tex" else "proxy_regressions.tex", replace = TRUE)
