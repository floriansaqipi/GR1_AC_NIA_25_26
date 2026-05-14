$ErrorActionPreference = "Stop"

$instances = @(
    @{ Name = "australia_iptv"; Input = "data/input/australia_iptv.json"; Output = "data/output_aco_tuning/australia"; SeedBase = 200 },
    @{ Name = "canada_pw"; Input = "data/input/canada_pw.json"; Output = "data/output_aco_tuning/canada"; SeedBase = 300 },
    @{ Name = "china_pw"; Input = "data/input/china_pw.json"; Output = "data/output_aco_tuning/china"; SeedBase = 400 },
    @{ Name = "croatia_tv"; Input = "data/input/croatia_tv_input.json"; Output = "data/output_aco_tuning/croatia"; SeedBase = 500 },
    @{ Name = "france_iptv"; Input = "data/input/france_iptv.json"; Output = "data/output_aco_tuning/france"; SeedBase = 600 },
    @{ Name = "germany_tv"; Input = "data/input/germany_tv_input.json"; Output = "data/output_aco_tuning/germany"; SeedBase = 700 },
    @{ Name = "kosovo_tv"; Input = "data/input/kosovo_tv_input.json"; Output = "data/output_aco_tuning/kosovo"; SeedBase = 800 },
    @{ Name = "netherlands_tv"; Input = "data/input/netherlands_tv_input.json"; Output = "data/output_aco_tuning/netherlands"; SeedBase = 900 },
    @{ Name = "singapore_pw"; Input = "data/input/singapore_pw.json"; Output = "data/output_aco_tuning/singapore"; SeedBase = 1000 },
    @{ Name = "spain_iptv"; Input = "data/input/spain_iptv.json"; Output = "data/output_aco_tuning/spain"; SeedBase = 1100 },
    @{ Name = "toy"; Input = "data/input/toy.json"; Output = "data/output_aco_tuning/toy"; SeedBase = 1200 },
    @{ Name = "uk_tv"; Input = "data/input/uk_tv_input.json"; Output = "data/output_aco_tuning/uk_tv"; SeedBase = 1400 }
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

foreach ($instance in $instances) {
    foreach ($run in $runs) {
        $seed = $instance.SeedBase + $run.SeedOffset
        Write-Host "Running $($instance.Name) $($run.Run) with seed $seed"

        python main.py `
            --algorithm aco `
            -i $instance.Input `
            -o $instance.Output `
            --run-id $run.Run `
            --ants $run.Ants `
            --iterations $run.Iterations `
            --alpha $run.Alpha `
            --beta $run.Beta `
            --rho $run.Rho `
            --candidate-cap $run.CandidateCap `
            --exploitation-prob $run.Exploitation `
            --memory-strength $run.Memory `
            --seed $seed `
            --verbose
    }
}
