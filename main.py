from parser.file_selector import select_file
from parser.parser import Parser
from serializer.serializer import SolutionSerializer
from scheduler.beam_search_scheduler import BeamSearchScheduler
from scheduler.rank_based_aco_scheduler import RankBasedAcoScheduler
from utils.utils import Utils
import argparse


def main():
    parser_arg = argparse.ArgumentParser(description="Run TV scheduling algorithms")
    parser_arg.add_argument("--algorithm", choices=["beam", "aco"], default="beam",
                            help="Scheduling algorithm to use")
    parser_arg.add_argument("--input", "-i", dest="input_file", help="Path to input JSON (optional)")
    parser_arg.add_argument("--output-dir", "-o", default="data/output_randomness",
                            help="Directory where the generated solution will be saved")
    parser_arg.add_argument("--restarts", type=int, default=3,
                            help="Number of randomized passes to try (large instances cap this automatically)")
    parser_arg.add_argument("--seed", type=int, default=None,
                            help="Optional random seed for reproducible randomized runs")
    parser_arg.add_argument("--disable-randomness", action="store_true",
                            help="Run only the deterministic beam search")
    parser_arg.add_argument("--verbose", action="store_true",
                            help="Print detailed scheduler logs")
    parser_arg.add_argument("--ants", type=int, default=8,
                            help="Number of ants for ACO")
    parser_arg.add_argument("--iterations", type=int, default=10,
                            help="Number of ACO iterations")
    parser_arg.add_argument("--alpha", type=float, default=1.0,
                            help="Pheromone importance for ACO")
    parser_arg.add_argument("--beta", type=float, default=2.0,
                            help="Heuristic importance for ACO")
    parser_arg.add_argument("--rho", type=float, default=0.15,
                            help="Pheromone evaporation rate for ACO")
    parser_arg.add_argument("--candidate-cap", type=int, default=15,
                            help="Maximum number of top candidate moves examined per ACO step")
    parser_arg.add_argument("--exploitation-prob", type=float, default=0.75,
                            help="Probability of taking the strongest current move in ACO")
    parser_arg.add_argument("--memory-strength", type=float, default=0.5,
                            help="How strongly time-transition memory influences ACO candidate selection")
    parser_arg.add_argument("--run-id", default=None,
                            help="Optional label used to keep outputs from different runs separate")

    # Advanced ACO controls are kept available, but hidden for simpler first-pass tuning.
    parser_arg.add_argument("--top-k", type=int, default=3, help=argparse.SUPPRESS)
    parser_arg.add_argument("--tau0", type=float, default=1.0, help=argparse.SUPPRESS)
    parser_arg.add_argument("--tau-min", type=float, default=0.1, help=argparse.SUPPRESS)
    parser_arg.add_argument("--tau-max", type=float, default=5.0, help=argparse.SUPPRESS)
    parser_arg.add_argument("--local-search-iters", type=int, default=8, help=argparse.SUPPRESS)
    parser_arg.add_argument("--time-bucket-size", type=int, default=60, help=argparse.SUPPRESS)
    
    args = parser_arg.parse_args()
    file_path = args.input_file if args.input_file else select_file()
    parser = Parser(file_path)
    instance = parser.parse()
    Utils.set_current_instance(instance)

    print("\nOpening time:", instance.opening_time)
    print("Closing time:", instance.closing_time)
    print(f"Total Channels: {len(instance.channels)}")

    lookahead = 4
    percentile = 25

    output_dir = args.output_dir
    if args.algorithm == "aco" and output_dir == "data/output_randomness":
        output_dir = "data/output_window_local_search" if args.local_search_iters > 0 else "data/output_aco_tuning"

    if args.algorithm == "aco":
        print('\nRunning Rank-Based ACO Scheduler')
        scheduler = RankBasedAcoScheduler(
            instance_data=instance,
            num_ants=args.ants,
            num_iterations=args.iterations,
            alpha=args.alpha,
            beta=args.beta,
            rho=args.rho,
            top_k=args.top_k,
            tau0=args.tau0,
            tau_min=args.tau_min,
            tau_max=args.tau_max,
            candidate_cap=args.candidate_cap,
            lookahead_limit=lookahead,
            density_percentile=percentile,
            exploitation_prob=args.exploitation_prob,
            local_search_iterations=args.local_search_iters,
            time_bucket_size=args.time_bucket_size,
            memory_strength=args.memory_strength,
            random_seed=args.seed,
            verbose=args.verbose
        )
    else:
        print('\nRunning Beam Search Scheduler')
        beam_width = 100
        scheduler = BeamSearchScheduler(
            instance_data=instance,
            beam_width=beam_width,
            lookahead_limit=lookahead,
            density_percentile=percentile,
            random_restarts=0 if args.disable_randomness else args.restarts,
            random_seed=args.seed,
            verbose=args.verbose
        )

    solution = scheduler.generate_solution()
    print(f"\n✓ Generated solution with total score: {solution.total_score}")

    if args.algorithm == "aco":
        algorithm_name = "aco_wls_rank" if args.local_search_iters > 0 else "aco_rank"
    else:
        algorithm_name = type(scheduler).__name__.lower()
    if args.algorithm == "beam" and not args.disable_randomness and args.restarts > 0:
        algorithm_name += "_random"

    serializer = SolutionSerializer(
        input_file_path=file_path,
        algorithm_name=algorithm_name,
        output_dir=output_dir,
        run_id=args.run_id
    )
    serializer.serialize(solution)

    print(f"✓ Solution saved to output file")


if __name__ == "__main__":
    main()
