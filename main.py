from parser.file_selector import select_file
from parser.parser import Parser
from serializer.serializer import SolutionSerializer
from scheduler.beam_search_scheduler import BeamSearchScheduler
from utils.utils import Utils
import argparse


def main():
    parser_arg = argparse.ArgumentParser(description="Run TV scheduling algorithms")
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
    
    args = parser_arg.parse_args()
    file_path = args.input_file if args.input_file else select_file()
    parser = Parser(file_path)
    instance = parser.parse()
    Utils.set_current_instance(instance)

    print("\nOpening time:", instance.opening_time)
    print("Closing time:", instance.closing_time)
    print(f"Total Channels: {len(instance.channels)}")

    print('\nRunning Beam Search Scheduler')
    
    # Default optimized parameters
    beam_width = 100
    lookahead = 4
    percentile = 25
    
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

    algorithm_name = type(scheduler).__name__.lower()
    if not args.disable_randomness and args.restarts > 0:
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
