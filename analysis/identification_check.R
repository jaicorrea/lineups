library(readr); library(dplyr)
df <- read_csv("../conditional_stats_with_baselines.csv", show_col_types = FALSE)
names(df) <- tolower(names(df))
df50 <- df %>% filter(num_pas > 50)

chk <- function(var, id) {
  df50 %>%
    group_by(.data[[id]]) %>%
    summarise(sd = sd(.data[[var]], na.rm = TRUE), n = n()) %>%
    ungroup() %>%
    summarise(
      total_ids = n(),
      ids_with_variation = sum(sd > 0 & !is.na(sd)),
      rows_from_varying_ids = sum(n[sd > 0 & !is.na(sd)])
    )
}

cat("z_focal_slg within focal_batter_id (num_pas>50 sample):\n")
print(chk("focal_season_slg", "focal_batter_id"))

cat("\nfocal_season_swing_path_tilt_median within focal_batter_id (num_pas>50 sample):\n")
print(chk("focal_season_swing_path_tilt_median", "focal_batter_id"))

cat("\nconditional_season_attack_angle_median within conditional_batter_id (num_pas>50 sample):\n")
print(chk("conditional_season_attack_angle_median", "conditional_batter_id"))

cat("\ncond_take_pct within conditional_batter_id (num_pas>50 sample):\n")
df50 <- df50 %>% mutate(cond_take_pct = 1 - conditional_season_swing_pct)
print(chk("cond_take_pct", "conditional_batter_id"))
