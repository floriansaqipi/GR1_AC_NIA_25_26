$ErrorActionPreference = "Stop"

$localSearchIterations = 8

$instances = @(
    @{ Name = "australia_iptv"; Input = "data/input/australia_iptv.json"; Output = "data/output_window_local_search/australia"; SeedBase = 200; StartRun = 11 },
    @{ Name = "canada_pw"; Input = "data/input/canada_pw.json"; Output = "data/output_window_local_search/canada"; SeedBase = 300; StartRun = 11 },
    @{ Name = "china_pw"; Input = "data/input/china_pw.json"; Output = "data/output_window_local_search/china"; SeedBase = 400; StartRun = 11 },
    @{ Name = "croatia_tv"; Input = "data/input/croatia_tv_input.json"; Output = "data/output_window_local_search/croatia"; SeedBase = 500; StartRun = 11 },
    @{ Name = "france_iptv"; Input = "data/input/france_iptv.json"; Output = "data/output_window_local_search/france"; SeedBase = 600; StartRun = 11 },
    @{ Name = "germany_tv"; Input = "data/input/germany_tv_input.json"; Output = "data/output_window_local_search/germany"; SeedBase = 700; StartRun = 11 },
    @{ Name = "kosovo_tv"; Input = "data/input/kosovo_tv_input.json"; Output = "data/output_window_local_search/kosovo"; SeedBase = 800; StartRun = 11 },
    @{ Name = "netherlands_tv"; Input = "data/input/netherlands_tv_input.json"; Output = "data/output_window_local_search/netherlands"; SeedBase = 900; StartRun = 11 },
    @{ Name = "singapore_pw"; Input = "data/input/singapore_pw.json"; Output = "data/output_window_local_search/singapore"; SeedBase = 1000; StartRun = 11 },
    @{ Name = "spain_iptv"; Input = "data/input/spain_iptv.json"; Output = "data/output_window_local_search/spain"; SeedBase = 1100; StartRun = 11 },
    @{ Name = "toy"; Input = "data/input/toy.json"; Output = "data/output_window_local_search/toy"; SeedBase = 1200; StartRun = 11 },
    @{ Name = "uk_tv"; Input = "data/input/uk_tv_input.json"; Output = "data/output_window_local_search/uk_tv"; SeedBase = 1400; StartRun = 11 }
)

$runs = @(
    @{ Run = "r11"; SeedOffset = 11; Ants = 12; Iterations = 10; Alpha = "1.3"; Beta = "2.0"; Rho = "0.10"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r12"; SeedOffset = 12; Ants = 14; Iterations = 10; Alpha = "1.0"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r13"; SeedOffset = 13; Ants = 14; Iterations = 10; Alpha = "1.3"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r14"; SeedOffset = 14; Ants = 16; Iterations = 10; Alpha = "1.3"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r15"; SeedOffset = 15; Ants = 14; Iterations = 12; Alpha = "1.3"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r16"; SeedOffset = 16; Ants = 16; Iterations = 12; Alpha = "1.3"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r17"; SeedOffset = 17; Ants = 14; Iterations = 10; Alpha = "1.4"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r18"; SeedOffset = 18; Ants = 16; Iterations = 10; Alpha = "1.4"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r19"; SeedOffset = 19; Ants = 14; Iterations = 10; Alpha = "1.3"; Beta = "2.0"; Rho = "0.10"; CandidateCap = 10; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r20"; SeedOffset = 20; Ants = 14; Iterations = 10; Alpha = "1.3"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 12; Exploitation = "0.80"; Memory = "0.50" },
    @{ Run = "r21"; SeedOffset = 21; Ants = 14; Iterations = 10; Alpha = "1.3"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.85"; Memory = "0.70" },
    @{ Run = "r22"; SeedOffset = 22; Ants = 16; Iterations = 10; Alpha = "1.3"; Beta = "2.0"; Rho = "0.15"; CandidateCap = 10; Exploitation = "0.85"; Memory = "0.70" }
)

function Get-RunNumber {
    param([string]$RunId)
    return [int]$RunId.Substring(1)
}

$startedAt = Get-Date
$totalRuns = 0
foreach ($instance in $instances) {
    $totalRuns += @($runs | Where-Object { (Get-RunNumber $_.Run) -ge $instance.StartRun }).Count
}
$completedRuns = 0

Write-Host "Starting ACO + Window Local Search full batch"
Write-Host "Running all configured instances from r11-r22"
Write-Host "Instances: $($instances.Count), total runs: $totalRuns"
Write-Host "Local search iterations: $localSearchIterations"
Write-Host ""

foreach ($instance in $instances) {
    New-Item -ItemType Directory -Force -Path $instance.Output | Out-Null

    $instanceRuns = @($runs | Where-Object { (Get-RunNumber $_.Run) -ge $instance.StartRun })
    foreach ($run in $instanceRuns) {
        $completedRuns += 1
        $seed = $instance.SeedBase + $run.SeedOffset
        Write-Host "[$completedRuns/$totalRuns] Running $($instance.Name) $($run.Run) with seed $seed"

        $commandArgs = @(
            "main.py",
            "--algorithm", "aco",
            "-i", $instance.Input,
            "-o", $instance.Output,
            "--run-id", $run.Run,
            "--ants", $run.Ants,
            "--iterations", $run.Iterations,
            "--alpha", $run.Alpha,
            "--beta", $run.Beta,
            "--rho", $run.Rho,
            "--candidate-cap", $run.CandidateCap,
            "--exploitation-prob", $run.Exploitation,
            "--memory-strength", $run.Memory,
            "--local-search-iters", $localSearchIterations,
            "--seed", $seed,
            "--verbose"
        )

        & python @commandArgs

        if ($LASTEXITCODE -ne 0) {
            throw "Run failed for $($instance.Name) $($run.Run) with exit code $LASTEXITCODE"
        }
    }
}

$elapsed = (Get-Date) - $startedAt
Write-Host ""
Write-Host "ACO + Window Local Search batch completed in $($elapsed.ToString())"
