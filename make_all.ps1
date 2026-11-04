# Rebuilds the paper's tables from the pooled pair data. Run from the repo root:  .\make_all.ps1
# Prerequisite (not run here, needs the raw Statcast pulls; see README "Getting the raw data"):
#   data code/pull_season.py, build_season.py, pool_seasons.py, attach_team.py, build_woba_outcomes.py
# which produce data/pooled/conditional_stats_with_woba_pooled_all_team.csv (committed, so this script works on a fresh clone).
# Set $env:RSCRIPT / $env:PYTHON if they are not on your PATH.
$ErrorActionPreference = "Continue"   # R writes package messages to stderr; failures are caught via exit codes
$root = $PSScriptRoot
$R = if ($env:RSCRIPT) { $env:RSCRIPT } else { "Rscript" }
$py = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$pooled = "../data/pooled/conditional_stats_with_woba_pooled_all_team.csv"

Push-Location "$root\analysis"
try {
    function Step($label, [scriptblock]$cmd) {
        Write-Host "== $label"; & $cmd
        if ($LASTEXITCODE -ne 0) { throw "$label failed (exit $LASTEXITCODE)" }
    }
    Step "Table 1 regressions, 2025"   { & $R table1_regressions.R $pooled 2025 }
    Step "Table 1 regressions, 2026"   { & $R table1_regressions.R $pooled 2026 }
    Step "Proxy regressions (pooled)"  { & $R proxy_regressions.R all }
    # Needs the pitch caches (statcast_pitch_cache_*), which are not in the repo. Skipped if absent;
    # trait_reliability.csv is committed.
    if (Test-Path "$root\statcast_pitch_cache_2025") { Step "Trait reliability" { & $py trait_reliability.py } }
    else { Write-Host "== Trait reliability: pitch caches not found, using committed trait_reliability.csv" }
    Step "Paper tables -> ../tables"   { & $R paper_tables.R }
} finally { Pop-Location }
Write-Host "Done. Tables are in $root\tables"

