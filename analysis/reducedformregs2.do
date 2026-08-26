import delimited "conditional_lineup_stats_2025.csv", clear

gen cond_take_pct = 1 - conditional_season_swing_pct

egen z_cond_ss = std(conditional_season_sweetspot_pct)
egen z_cond_aa = std(conditional_season_attack_angle_)
egen z_cond_ad = std(conditional_season_attack_direct)
egen z_cond_tilt = std(conditional_season_swing_path_ti)
egen z_cond_gb = std(conditional_season_groundball_pc)
egen z_cond_fb = std(conditional_season_flyball_pct)
egen z_cond_ld = std(conditional_season_linedrive_pct)
egen z_cond_pu = std(conditional_season_popup_pct)
egen z_cond_chase = std(conditional_season_chase_pct)
egen z_cond_swstr = std(conditional_season_swstr_pct)
egen z_cond_take = std(cond_take_pct)

egen z_focal_ss = std(focal_season_sweetspot_pct)
egen z_focal_aa = std(focal_season_attack_angle_)
egen z_focal_ad = std(focal_season_attack_direct)
egen z_focal_tilt = std(focal_season_swing_path_ti)
egen z_focal_gb = std(focal_season_groundball_pc)
egen z_focal_fb = std(focal_season_flyball_pct)
egen z_focal_ld = std(focal_season_linedrive_pct)
egen z_focal_pu = std(focal_season_popup_pct)
egen z_focal_chase = std(focal_season_chase_pct)
egen z_focal_swstr = std(focal_season_swstr_pct)

reghdfe focal_delta_run_exp_pa c.z_cond_ss##c.z_focal_aa [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_ld##c.z_focal_tilt [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_chase##c.z_focal_ad [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_swstr##c.z_focal_ad [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_gb##c.z_focal_aa [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_fb##c.z_focal_tilt [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_take##c.z_focal_aa [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_ss##c.z_focal_aa c.z_cond_ld##c.z_focal_tilt c.z_cond_chase##c.z_focal_ad c.z_cond_swstr##c.z_focal_ad [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_ss##c.z_focal_aa c.z_cond_ld##c.z_focal_tilt c.z_cond_chase##c.z_focal_ad c.z_cond_swstr##c.z_focal_ad [fw=num_pas] if num_pas > 50, absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)
