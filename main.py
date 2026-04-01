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
    parser_arg.add_argument("--top-k", type=int, default=3,
                            help="How many top ants reinforce pheromones in ACO")
    parser_arg.add_argument("--candidate-cap", type=int, default=15,
                            help="Maximum number of top candidate moves examined per ACO step")
    
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
            candidate_cap=args.candidate_cap,
            lookahead_limit=lookahead,
            density_percentile=percentile,
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

    algorithm_name = "aco_rank" if args.algorithm == "aco" else type(scheduler).__name__.lower()
    if args.algorithm == "beam" and not args.disable_randomness and args.restarts > 0:
        algorithm_name += "_random"

    serializer = SolutionSerializer(
        input_file_path=file_path,
        algorithm_name=algorithm_name,
        output_dir=args.output_dir
    )
    serializer.serialize(solution)

    print(f"✓ Solution saved to output file")


if __name__ == "__main__":
    main()
