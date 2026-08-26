import delimited "conditional_stats_with_baselines.csv", clear

gen focal_delta_run_diff = focal_delta_run_exp_pa - focal_season_delta_run_exp_pa

* -----------------------------------------------------------------------------
* Basic diagnostics: check if "season" traits vary within player IDs
* (If they do, main effects are not absorbed by player-only FE.)
* -----------------------------------------------------------------------------
bys conditional_batter_id: egen sd_cond_season_obp = sd(conditional_season_obp)
bys focal_batter_id:       egen sd_focal_season_slg = sd(focal_season_slg)

quietly count if sd_cond_season_obp > 0 & !missing(sd_cond_season_obp)
display "Rows with within-conditional_id variation in conditional_season_obp: " r(N)
quietly count if sd_focal_season_slg > 0 & !missing(sd_focal_season_slg)
display "Rows with within-focal_id variation in focal_season_slg: " r(N)

* -----------------------------------------------------------------------------
* Pairing-mechanism proxies available in this dataset
* -----------------------------------------------------------------------------
gen cond_take_pct = 1 - conditional_season_swing_pct
gen same_side = (focal_hitterside == conditional_hitterside) if !missing(focal_hitterside, conditional_hitterside)
gen opp_side = 1 - same_side if !missing(same_side)

gen swing_gap = focal_season_swing_pct - conditional_season_swing_pct
gen contact_gap = focal_season_contact_pct - conditional_season_contact_pct
gen abs_swing_gap = abs(swing_gap)
gen abs_contact_gap = abs(contact_gap)

egen z_cond_obp = std(conditional_season_obp)
egen z_cond_take = std(cond_take_pct)
egen z_cond_contact = std(conditional_season_contact_pct)
egen z_cond_barrel = std(conditional_season_barrel_pa)
egen z_focal_slg = std(focal_season_slg)
egen z_focal_barrel = std(focal_season_barrel_pa)
egen z_abs_swing_gap = std(abs_swing_gap)
egen z_abs_contact_gap = std(abs_contact_gap)

* Ensure frequency weights are integer-like counts.
assert num_pas == floor(num_pas)

reg focal_delta_run_exp_pa c.conditional_season_obp##c.focal_season_slg

reg focal_delta_run_diff conditional_season_obp

reg focal_delta_run_diff c.conditional_season_obp##c.focal_season_slg


reg focal_delta_run_diff c.conditional_season_obp##c.focal_season_slg ///
    [aweight=num_pas], vce(cluster focal_batter_id)
	
reghdfe focal_delta_run_exp_pa c.conditional_season_obp##c.focal_season_slg ///
    [fw=num_pas] if num_pas>50, absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

	
egen z_obp = std(conditional_season_obp)
egen z_slg = std(focal_season_slg)
reg focal_delta_run_diff c.z_obp##c.z_slg 


xtile q_obp = conditional_season_obp, nq(4)
xtile q_slg = focal_season_slg, nq(4)
reg focal_delta_run_diff i.q_obp##i.q_slg 


* -----------------------------------------------------------------------------
* Complementarity battery (reghdfe)
* Outcome: focal_delta_run_exp_pa
* FE: focal and conditional batter IDs
* Weight: num_pas as frequency weight
* -----------------------------------------------------------------------------

* 0) Baseline OBP x SLG with FE
reghdfe focal_delta_run_exp_pa c.z_cond_obp##c.z_focal_slg ///
    [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

* 1) Discipline -> Power complementarity
* More patient prior hitter (higher take%) paired with power focal hitter
reghdfe focal_delta_run_exp_pa c.z_cond_take##c.z_focal_slg ///
    [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

* 2) Contact -> Power complementarity
reghdfe focal_delta_run_exp_pa c.z_cond_contact##c.z_focal_slg ///
    [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

* 3) Prior hard-contact profile -> focal power
reghdfe focal_delta_run_exp_pa c.z_cond_barrel##c.z_focal_slg ///
    [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

* 4) OBP -> focal barrel skill (alternative focal power proxy)
reghdfe focal_delta_run_exp_pa c.z_cond_obp##c.z_focal_barrel ///
    [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

* 5) Handedness sequencing x focal power
reghdfe focal_delta_run_exp_pa i.opp_side##c.z_focal_slg ///
    [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

* 6) Approach contrast (bigger style gap between hitters)
reghdfe focal_delta_run_exp_pa c.z_abs_swing_gap##c.z_focal_slg ///
    [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_abs_contact_gap##c.z_focal_slg ///
    [fw=num_pas], absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

* 7) Higher-support sample only
reghdfe focal_delta_run_exp_pa c.z_cond_obp##c.z_focal_slg ///
    [fw=num_pas] if num_pas > 50, absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)

reghdfe focal_delta_run_exp_pa c.z_cond_take##c.z_focal_slg ///
    [fw=num_pas] if num_pas > 50, absorb(focal_batter_id conditional_batter_id) vce(cluster focal_batter_id)



/*
keep if num_pas>=40

reg focal_delta_run_exp_pa c.conditional_season_obp##c.focal_season_slg

reg focal_delta_run_diff conditional_season_obp

reg focal_delta_run_diff c.conditional_season_obp##c.focal_season_slg

