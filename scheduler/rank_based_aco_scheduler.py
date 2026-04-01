from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
import bisect
import random

from models.schedule import Schedule
from models.solution import Solution
from scheduler.beam_search_scheduler import BeamSearchScheduler


class RankBasedAcoScheduler(BeamSearchScheduler):
    """
    Practical rank-based ACO scheduler.

    It reuses the existing preprocessing, constraint checks, and candidate
    generation from BeamSearchScheduler, but replaces beam expansion with
    probabilistic ant-based solution construction.
    """
    START_TOKEN = "__START__"

    def __init__(self,
                 instance_data,
                 num_ants: int = 8,
                 num_iterations: int = 10,
                 alpha: float = 1.0,
                 beta: float = 2.0,
                 rho: float = 0.15,
                 top_k: int = 3,
                 tau0: float = 1.0,
                 tau_min: float = 0.1,
                 tau_max: float = 5.0,
                 candidate_cap: int = 15,
                 lookahead_limit: int = 4,
                 density_percentile: int = 25,
                 random_seed: Optional[int] = None,
                 verbose: bool = True):
        super().__init__(
            instance_data=instance_data,
            beam_width=max(50, candidate_cap),
            lookahead_limit=lookahead_limit,
            density_percentile=density_percentile,
            random_restarts=0,
            random_seed=random_seed,
            verbose=verbose
        )
        self.num_ants = max(1, num_ants)
        self.num_iterations = max(1, num_iterations)
        self.alpha = max(0.0, alpha)
        self.beta = max(0.0, beta)
        self.rho = min(max(0.01, rho), 0.95)
        self.top_k = max(1, top_k)
        self.tau0 = max(0.01, tau0)
        self.tau_min = max(0.001, tau_min)
        self.tau_max = max(self.tau_min, tau_max)
        self.candidate_cap = max(3, candidate_cap)
        self.pheromones: Dict[str, float] = {}
        self.transition_pheromones: Dict[Tuple[str, str], float] = {}

        # Runtime-tuned values; finalized in generate_solution().
        self.effective_num_ants = self.num_ants
        self.effective_num_iterations = self.num_iterations
        self.effective_top_k = self.top_k
        self.effective_candidate_cap = self.candidate_cap
        self.exploitation_prob = 0.75
        self.local_search_iterations = 8

    def _reset_pheromones(self):
        self.pheromones = {
            prog_id: self.tau0
            for prog_id in self.prog_by_id.keys()
        }
        self.transition_pheromones = {}

    def _tune_runtime(self):
        """Adapt ACO parameters so large instances stay practical."""
        if self.n_channels > 300:
            self.effective_num_ants = min(self.num_ants, 4)
            self.effective_num_iterations = min(self.num_iterations, 6)
            self.effective_top_k = min(self.top_k, 2)
            self.effective_candidate_cap = min(self.candidate_cap, 8)
            self.lookahead_limit = min(self.lookahead_limit, 1)
            self.allow_intermediate_stops = False
            self.exploitation_prob = 0.88
            self.local_search_iterations = 0
        elif self.n_channels > 120:
            self.effective_num_ants = min(self.num_ants, 6)
            self.effective_num_iterations = min(self.num_iterations, 8)
            self.effective_top_k = min(self.top_k, 2)
            self.effective_candidate_cap = min(self.candidate_cap, 10)
            self.lookahead_limit = min(self.lookahead_limit, 2)
            self.allow_intermediate_stops = False
            self.exploitation_prob = 0.82
            self.local_search_iterations = 3
        elif self.n_channels > 50:
            self.effective_num_ants = min(self.num_ants, 8)
            self.effective_num_iterations = min(self.num_iterations, 10)
            self.effective_top_k = min(self.top_k, 3)
            self.effective_candidate_cap = min(self.candidate_cap, 12)
            self.lookahead_limit = min(self.lookahead_limit, 3)
            self.allow_intermediate_stops = True
            self.exploitation_prob = 0.76
            self.local_search_iterations = 6
        else:
            self.effective_num_ants = self.num_ants
            self.effective_num_iterations = self.num_iterations
            self.effective_top_k = self.top_k
            self.effective_candidate_cap = self.candidate_cap
            self.allow_intermediate_stops = True
            self.exploitation_prob = 0.70
            self.local_search_iterations = 10

    def _transition_key(self, prev_prog_id: Optional[str], next_prog_id: str) -> Tuple[str, str]:
        return (prev_prog_id or self.START_TOKEN, next_prog_id)

    def _candidate_weight(self, candidate, heuristic_value: float, prev_prog_id: Optional[str]) -> float:
        node_tau = self.pheromones.get(candidate[3].unique_id, self.tau0)
        edge_tau = self.transition_pheromones.get(
            self._transition_key(prev_prog_id, candidate[3].unique_id),
            self.tau0
        )
        tau = max(self.tau_min, (node_tau * edge_tau) ** 0.5)
        eta = max(1.0, heuristic_value)
        return (tau ** self.alpha) * (eta ** self.beta)

    def _select_candidate(self,
                          candidates,
                          rng: random.Random,
                          prev_prog_id: Optional[str],
                          force_best: bool = False):
        if len(candidates) == 1:
            return candidates[0]

        priorities = [self._candidate_priority(candidate) for candidate in candidates]
        min_priority = min(priorities)
        heuristic_values = [priority - min_priority + 1.0 for priority in priorities]
        weights = [
            self._candidate_weight(candidate, heuristic_value, prev_prog_id)
            for candidate, heuristic_value in zip(candidates, heuristic_values)
        ]
        best_idx = max(range(len(candidates)), key=lambda idx: weights[idx])

        if force_best or rng.random() < self.exploitation_prob:
            return candidates[best_idx]

        total_weight = sum(weights)

        if total_weight <= 0:
            return candidates[0]

        pick = rng.random() * total_weight
        cumulative = 0.0

        for candidate, weight in zip(candidates, weights):
            cumulative += weight
            if pick <= cumulative:
                return candidate

        return candidates[-1]

    def _construct_ant_solution(self, rng: random.Random, force_best: bool = False) -> Solution:
        closing = self.instance_data.closing_time
        time = self.instance_data.opening_time
        prev_ch: Optional[int] = None
        prev_genre = ""
        prev_prog_id: Optional[str] = None
        genre_streak = 0
        used_programs: Set[str] = set()
        scheduled: List[Schedule] = []
        total_score = 0

        while time < closing:
            candidates = self._get_candidates(time, prev_ch, prev_genre, genre_streak, used_programs)

            if not candidates:
                idx = bisect.bisect_right(self.times, time)
                if idx < len(self.times) and self.times[idx] < closing:
                    time = self.times[idx]
                    continue
                break

            candidates.sort(key=self._candidate_priority, reverse=True)
            candidates = candidates[:self.effective_candidate_cap]
            seg_score, ch_idx, ch_id, prog, seg_start, seg_end = self._select_candidate(
                candidates,
                rng,
                prev_prog_id=prev_prog_id,
                force_best=force_best
            )

            scheduled.append(Schedule(
                program_id=prog.program_id,
                channel_id=ch_id,
                start=seg_start,
                end=seg_end,
                fitness=seg_score,
                unique_program_id=prog.unique_id
            ))

            total_score += seg_score
            used_programs.add(prog.unique_id)
            if prog.genre == prev_genre:
                genre_streak += 1
            else:
                genre_streak = 1
                prev_genre = prog.genre

            prev_ch = ch_id
            prev_prog_id = prog.unique_id
            time = seg_end

        return Solution(scheduled, total_score)

    def _evaporate_pheromones(self):
        evaporation_factor = 1.0 - self.rho
        for prog_id in self.pheromones:
            evaporated = self.pheromones[prog_id] * evaporation_factor
            self.pheromones[prog_id] = min(self.tau_max, max(self.tau_min, evaporated))
        for edge_key in list(self.transition_pheromones.keys()):
            evaporated = self.transition_pheromones[edge_key] * evaporation_factor
            self.transition_pheromones[edge_key] = min(self.tau_max, max(self.tau_min, evaporated))

    def _deposit_solution(self, solution: Solution, rank_weight: float, quality_multiplier: float = 1.0):
        solution_total = max(1.0, float(solution.total_score))
        prev_prog_id: Optional[str] = None

        for scheduled in solution.scheduled_programs:
            contribution = max(0.0, float(scheduled.fitness)) / solution_total
            if contribution <= 0:
                prev_prog_id = scheduled.unique_program_id
                continue

            delta = rank_weight * quality_multiplier * contribution
            prog_id = scheduled.unique_program_id
            reinforced_node = self.pheromones.get(prog_id, self.tau0) + delta
            self.pheromones[prog_id] = min(self.tau_max, max(self.tau_min, reinforced_node))

            edge_key = self._transition_key(prev_prog_id, prog_id)
            reinforced_edge = self.transition_pheromones.get(edge_key, self.tau0) + delta
            self.transition_pheromones[edge_key] = min(self.tau_max, max(self.tau_min, reinforced_edge))
            prev_prog_id = prog_id

    def _deposit_pheromones(self, ranked_solutions: List[Solution], global_best: Solution):
        if not ranked_solutions:
            return

        iteration_best_score = max(1.0, float(ranked_solutions[0].total_score))

        for rank_idx, solution in enumerate(ranked_solutions[:self.effective_top_k]):
            rank_weight = self.effective_top_k - rank_idx
            quality_multiplier = max(0.25, float(solution.total_score) / iteration_best_score)
            self._deposit_solution(solution, rank_weight, quality_multiplier)

        if global_best.scheduled_programs:
            self._deposit_solution(global_best, self.effective_top_k + 1, 1.0)

    def generate_solution(self) -> Solution:
        self._tune_runtime()
        self._reset_pheromones()

        if self.verbose:
            print(f"\n{'='*70}")
            print("RANK-BASED ACO SCHEDULER")
            print(f"Channels: {self.n_channels}")
            print(f"Ants: {self.effective_num_ants}, Iterations: {self.effective_num_iterations}")
            print(f"alpha={self.alpha}, beta={self.beta}, rho={self.rho}")
            print(f"Candidate cap: {self.effective_candidate_cap}, Top-k: {self.effective_top_k}")
            print(f"Exploitation probability: {self.exploitation_prob:.2f}, Local search iterations: {self.local_search_iterations}")
            print(f"Lookahead: {self.lookahead_limit}, Intermediate stops: {'on' if self.allow_intermediate_stops else 'off'}")
            print(f"{'='*70}\n")

        base_seed = self.random_seed if self.random_seed is not None else random.randrange(1, 10**9)
        global_best = Solution([], 0)

        for iteration in range(self.effective_num_iterations):
            iteration_solutions: List[Solution] = []

            for ant_idx in range(self.effective_num_ants):
                ant_rng = random.Random(base_seed + iteration * 1000 + ant_idx)
                solution = self._construct_ant_solution(ant_rng, force_best=(ant_idx == 0))
                iteration_solutions.append(solution)

            iteration_solutions.sort(key=lambda solution: solution.total_score, reverse=True)
            iteration_best = iteration_solutions[0]

            if iteration_best.total_score > global_best.total_score:
                global_best = iteration_best

            self._evaporate_pheromones()
            self._deposit_pheromones(iteration_solutions, global_best)

            if self.verbose:
                print(
                    f"Iteration {iteration + 1}/{self.effective_num_iterations}: "
                    f"best={iteration_best.total_score}, global_best={global_best.total_score}"
                )

        if self.local_search_iterations > 0 and global_best.scheduled_programs:
            improved = self._local_search(global_best, max_iter=self.local_search_iterations)
            if improved.total_score > global_best.total_score:
                global_best = improved

        if self.verbose:
            print(f"\n{'='*70}")
            print(f"BEST: Score={global_best.total_score}, Programs={len(global_best.scheduled_programs)}")
            print(f"{'='*70}\n")

        return global_best
