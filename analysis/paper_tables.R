# Builds the paper's descriptive tables (pair PA distribution, trait reliability, expected signs)
# into ../tables/. Usage (from analysis/):  Rscript paper_tables.R
library(readr); library(dplyr)
out <- "../tables"; dir.create(out, showWarnings = FALSE)
df <- read_csv("../data/pooled/conditional_stats_with_woba_pooled_all_team.csv", show_col_types = FALSE)
names(df) <- tolower(names(df))
fmt <- function(x) formatC(x, format = "d", big.mark = ",")

# ---- Table: distribution of pairs by PAs per pair ----
bins <- c("1--30", "31--50", "51--75", "76--100", "101+")
panel <- function(d, label) {
  d$bin <- cut(d$num_pas, c(0, 30, 50, 75, 100, Inf), labels = bins)
  g <- d %>% group_by(bin) %>% summarise(n = n(), pa = sum(num_pas), .groups = "drop")
  tn <- sum(g$n); tp <- sum(g$pa)
  c(sprintf("\\multicolumn{5}{l}{\\textit{%s}} \\\\", label),
    sprintf("%s & %s & %.1f & %s & %.1f \\\\", g$bin, fmt(g$n), 100 * g$n / tn, fmt(g$pa), 100 * g$pa / tp),
    "\\addlinespace",
    sprintf("Total & %s & 100.0 & %s & 100.0 \\\\", fmt(tn), fmt(tp)))
}
tex <- c("\\begin{table}[H]", "\\centering", "\\small",
  "\\caption{Distribution of pairs and regression weight by plate appearances per pair}",
  "\\label{tab:pair_pa_distribution}", "\\begin{tabular}{lrrrr}", "\\toprule",
  "PAs per pair & Pairs & \\% of pairs & PAs (weight) & \\% of weight \\\\", "\\midrule",
  panel(filter(df, season == 2025), "Panel A: 2025"), "\\midrule",
  panel(filter(df, season == 2026), "Panel B: 2026"),
  "\\bottomrule", "\\end{tabular}",
  "\\par\\smallskip\\parbox{0.9\\textwidth}{\\footnotesize \\textit{Notes:} Each observation is a (focal hitter, conditional hitter) pair within a season. PAs per pair is the number of plate appearances in which the focal hitter batted directly behind the conditional hitter. The regressions weight each pair by this number, so the weight share equals the share of total pair PAs. Hitters with fewer than 50 PA in a season are excluded, and no minimum is imposed on PAs per pair.}",
  "\\end{table}")
writeLines(tex, file.path(out, "pair_pa_distribution.tex"))

# ---- Table: split-half reliability (2025, 2026 from trait_reliability.csv) ----
r <- read_csv("trait_reliability.csv", show_col_types = FALSE)
esc <- function(s) gsub("%", "\\\\%", s)
tex <- c("\\begin{table}[H]", "\\centering", "\\caption{Split-half reliability of hitter traits}",
  "\\label{tab:reliab}", "\\begin{tabular}{lcc}", "\\toprule", "Trait & 2025 & 2026 \\\\", "\\midrule",
  sprintf("%s & %.2f & %.2f \\\\", esc(r$trait), r$`2025`, r$`2026`),
  "\\bottomrule", "\\end{tabular}", "", "\\vspace{4pt}",
  "\\begin{minipage}{0.8\\textwidth}", "\\centering\\footnotesize",
  "\\textit{Notes:} Odd/even split of each hitter's plate appearances, Spearman--Brown corrected.",
  "\\end{minipage}", "\\end{table}")
writeLines(tex, file.path(out, "trait_reliability.tex"))

# ---- Tables: expected sign of beta_3 (focal and conditional outcome) ----
rows <- list(
 c("On-base percentage (OBP)","Slugging (SLG)","+"), c("Absolute contact gap$^{\\dagger}$","Slugging (SLG)","+"),
 c("Sweet spot \\%","Attack angle","+"), c("Line-drive \\%","Swing path tilt","+"),
 c("Chase \\%","Attack direction","--"), c("Swing path tilt","Swinging-strike \\%","--"),
 c("Nitro dist","Attack direction","--"), c("Attack angle","Chase \\%","--"),
 c("Swing path tilt","Attack angle","--"), c("Contact \\%","Barrel/PA","+"),
 c("Chase \\%","Swing \\%","--"), c("Pitch/PA","Swing path tilt","+"))
exp_tab <- function(outcome, label) c("\\begin{table}[htbp]", "\\centering",
  sprintf("\\caption{Expected sign of the interaction coefficient $\\beta_3$ on %s}", outcome),
  sprintf("\\label{tab:%s}", label), "\\begin{tabular}{c l l c}", "\\toprule",
  "No. & Conditional trait & Focal trait & Expected sign \\\\", "\\midrule",
  vapply(seq_along(rows), function(i) sprintf("%d & %s & %s & %s \\\\", i, rows[[i]][1], rows[[i]][2], rows[[i]][3]), ""),
  "\\bottomrule", "\\end{tabular}", "", "\\vspace{4pt}", "\\begin{minipage}{0.8\\textwidth}", "\\centering", "\\footnotesize",
  "\\textit{Notes:} $^{\\dagger}$ Absolute contact gap is the absolute value of the difference between the conditional and focal hitter's Contact\\%.",
  "\\end{minipage}", "\\end{table}")
writeLines(exp_tab("focal $\\Delta$ Run Expectancy", "expectations_focal"), file.path(out, "expected_signs_focal.tex"))
writeLines(exp_tab("conditional $\\Delta$ Run Expectancy", "expectations_cond"), file.path(out, "expected_signs_cond.tex"))

# ---- Table: composition by pair handedness ----
df$same <- df$focal_hitterside == df$conditional_hitterside
side <- function(d, lab) {
  g <- d %>% group_by(same) %>% summarise(n = n(), pa = sum(num_pas), .groups = "drop") %>% arrange(desc(same))
  sprintf("%s & %s & %s & %.1f & %s & %.1f \\\\", c(lab, ""), c("Same-side", "Opposite-side"),
          fmt(g$n), 100 * g$n / sum(g$n), fmt(g$pa), 100 * g$pa / sum(g$pa))
}
tex <- c("\\begin{table}[htbp]", "\\centering", "\\caption{Composition of the sample by pair handedness}",
  "\\label{tab:pair_side}", "\\begin{tabular}{llrrrr}", "\\hline\\hline",
  "Sample & Pair type & Pairs & \\% of pairs & PAs & \\% of PAs \\\\", "\\hline",
  side(df, "Pooled"), "\\hline", side(filter(df, season == 2025), "2025"), "\\hline",
  side(filter(df, season == 2026), "2026"), "\\hline\\hline", "\\end{tabular}", "\\par\\smallskip", "\\footnotesize",
  "\\textit{Notes:} A pair is same-side when the focal and conditional hitters bat from the same side (switch-hitters are assigned the side recorded in the data). PAs are the sum of \\texttt{num\\_pas} across pairs.",
  "\\end{table}")
writeLines(tex, file.path(out, "pair_side_composition.tex"))

# ---- Regression tables: copied from table1_regressions.R / proxy_regressions.R output, captions as in the paper ----
# Run table1_regressions.R (2025 and 2026) and proxy_regressions.R first.
for (k in c("focal", "cond")) for (y in c(2025, 2026)) {
  s <- paste(readLines(sprintf("table1_%s_%d.tex", k, y)), collapse = "\n")
  s <- sub("delta run expectancy\\}", sprintf("$\\\\Delta$ Run Expectancy, %d}", y), s)
  writeLines(s, file.path(out, sprintf("interaction_%s_%d.tex", k, y)))
}
for (y in c(2025, 2026)) {
  s <- paste(readLines(sprintf("table1_barrel_%d.tex", y)), collapse = "\n")
  s <- sub("Barrel/PA\\}", sprintf("Barrel/PA, %d}", y), s)
  writeLines(s, file.path(out, sprintf("interaction_barrel_%d.tex", y)))
}
p <- paste(readLines("proxy_regressions_pooled.tex"), collapse = "\n")
p <- sub("^\\s*\\\\begingroup\\s*\\\\centering\\s*", "", p)
p <- sub("\\\\par \\\\raggedright.*$", "", p)
writeLines(c("\\begin{table}[H]", "\\centering", "\\caption{Barrel/PA and wOBA as proxies for run expectancy}",
  "\\label{tab:proxy}", trimws(p, "right"), "", "\\vspace{4pt}", "\\begin{minipage}{0.8\\textwidth}", "\\centering\\footnotesize",
  "\\textit{Notes:} 2025--2026 hitter-seasons, weighted by plate appearances. Standard errors clustered by hitter in parentheses. $^{***}p<0.01$, $^{**}p<0.05$, $^{*}p<0.1$.",
  "\\end{minipage}", "\\end{table}"), file.path(out, "proxy_regressions.tex"))
