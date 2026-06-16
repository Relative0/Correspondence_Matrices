$ErrorActionPreference = "Stop"

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  $py = "python"
}

$commonDisabled = @(
  "--no-dd", "--no-espresso", "--no-sympy", "--no-robdd", "--no-bdd-sop", "--no-numba"
)

& $py .\cm_bench.py `
  --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 --expr-style ordinary `
  --out-prefix paper_exact --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate `
  --cm-use-persistent-cache --cm-eval-repeat 50 --cm-hybrid-threshold 7 `
  @commonDisabled --print-summary

& $py .\cm_bench.py `
  --sizes 16,20,24,28,32 --trials 3 --max-depth 4 --seed 123 --expr-style ordinary `
  --out-prefix paper_large_n --cm-layout balanced --cm-compare-no-reinflate `
  --cm-use-persistent-cache --cm-eval-repeat 50 --cm-hybrid-threshold 7 `
  --cm-report-ir-breakdown --large-n-safe @commonDisabled --print-summary

$robustness = @()
foreach ($seed in 123,456,789,2025,31415) {
  $prefix = "paper_robustness_seed_$seed"
  & $py .\cm_bench.py `
    --sizes 16,20,24,28,32 --trials 3 --max-depth 4 --seed $seed --expr-style ordinary `
    --out-prefix $prefix --cm-layout balanced --cm-compare-no-reinflate `
    --cm-use-persistent-cache --cm-eval-repeat 50 --cm-hybrid-threshold 7 `
    --cm-report-ir-breakdown --large-n-safe @commonDisabled
  foreach ($row in (Import-Csv ".\${prefix}_summary.csv")) {
    $row | Add-Member -NotePropertyName seed -NotePropertyValue $seed
    $robustness += $row
  }
}
$robustness | Export-Csv .\paper_robustness_summary.csv -NoTypeInformation

$stress = @()
foreach ($style in "ordinary","broad","low-reuse","anti-reduction") {
  $prefix = "paper_stress_$($style -replace '-','_')"
  & $py .\cm_bench.py `
    --sizes 16,20,24,28,32 --trials 3 --max-depth 4 --seed 123 --expr-style $style `
    --out-prefix $prefix --cm-layout balanced --cm-compare-no-reinflate `
    --cm-use-persistent-cache --cm-eval-repeat 50 --cm-hybrid-threshold 7 `
    --cm-report-ir-breakdown --large-n-safe @commonDisabled
  $stress += Import-Csv ".\${prefix}_summary.csv"
}
$stress | Export-Csv .\paper_stress_summary.csv -NoTypeInformation

$sampled = @()
foreach ($seed in 123,456,789) {
  $prefix = "paper_sampled_seed_$seed"
  & $py .\cm_bench.py `
    --sizes 20,24,28,32 --trials 1 --max-depth 4 --seed $seed --expr-style ordinary `
    --out-prefix $prefix --cm-layout balanced --cm-compare-no-reinflate `
    --cm-use-persistent-cache --cm-eval-repeat 50 --cm-hybrid-threshold 7 `
    --large-n-safe --sampled-correctness 1000 @commonDisabled
  foreach ($row in (Import-Csv ".\${prefix}_summary.csv")) {
    $row | Add-Member -NotePropertyName seed -NotePropertyValue $seed
    $sampled += $row
  }
}
$sampled | Export-Csv .\paper_sampled_correctness_summary.csv -NoTypeInformation
