from __future__ import annotations

from typing import Dict, List, Optional, Tuple
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
                 exploitation_prob: float = 0.75,
                 local_search_iterations: int = 8,
                 time_bucket_size: int = 60,
                 memory_strength: float = 0.5,
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
        self.time_transition_memory: Dict[Tuple[int, int, int, str], float] = {}

        # User-tuned values; preserved as given for experimentation.
        self.effective_num_ants = self.num_ants
        self.effective_num_iterations = self.num_iterations
        self.effective_top_k = self.top_k
        self.effective_candidate_cap = self.candidate_cap
        self.exploitation_prob = min(max(0.0, exploitation_prob), 1.0)
        self.local_search_iterations = max(0, local_search_iterations)
        self.time_bucket_size = max(15, time_bucket_size)
        self.memory_strength = max(0.0, memory_strength)
        self.time_memory_max = 3.0

    def _reset_pheromones(self):
        self.pheromones = {
            prog_id: self.tau0
            for prog_id in self.prog_by_id.keys()
        }
        self.transition_pheromones = {}
        self.time_transition_memory = {}

    def _tune_runtime(self):
        """
        Respect user-provided ACO parameters during tuning experiments.
        We keep only basic safety normalization here.
        """
        self.effective_num_ants = self.num_ants
        self.effective_num_iterations = self.num_iterations
        self.effective_top_k = min(self.top_k, self.effective_num_ants)
        self.effective_candidate_cap = self.candidate_cap
        self.allow_intermediate_stops = True

    def _transition_key(self, prev_prog_id: Optional[str], next_prog_id: str) -> Tuple[str, str]:
        return (prev_prog_id or self.START_TOKEN, next_prog_id)

    def _time_bucket(self, time: int) -> int:
        return max(0, (time - self.instance_data.opening_time) // self.time_bucket_size)

    def _time_transition_key(self,
                             time: int,
                             prev_channel_id: Optional[int],
                             next_channel_id: int,
                             next_genre: str) -> Tuple[int, int, int, str]:
        return (
            self._time_bucket(time),
            -1 if prev_channel_id is None else prev_channel_id,
            next_channel_id,
            next_genre
        )

    def _candidate_weight(self,
                          candidate,
                          heuristic_value: float,
                          prev_prog_id: Optional[str],
                          prev_ch_id: Optional[int]) -> float:
        node_tau = self.pheromones.get(candidate[3].unique_id, self.tau0)
        edge_tau = self.transition_pheromones.get(
            self._transition_key(prev_prog_id, candidate[3].unique_id),
            self.tau0
        )
        tau = max(self.tau_min, (node_tau * edge_tau) ** 0.5)
        eta = max(1.0, heuristic_value)
        memory_key = self._time_transition_key(candidate[4], prev_ch_id, candidate[2], candidate[3].genre)
        memory_factor = 1.0 + self.memory_strength * self.time_transition_memory.get(memory_key, 0.0)
        return (tau ** self.alpha) * (eta ** self.beta) * memory_factor

    def _select_candidate(self,
                          candidates,
                          rng: random.Random,
                          prev_prog_id: Optional[str],
                          prev_ch_id: Optional[int],
                          force_best: bool = False):
        if len(candidates) == 1:
            return candidates[0]

        priorities = [self._candidate_priority(candidate) for candidate in candidates]
        min_priority = min(priorities)
        heuristic_values = [priority - min_priority + 1.0 for priority in priorities]
        weights = [
            self._candidate_weight(candidate, heuristic_value, prev_prog_id, prev_ch_id)
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

    def _construct_ant_solution(self,
                                rng: random.Random,
                                force_best: bool = False) -> Solution:
        closing = self.instance_data.closing_time
        time = self.instance_data.opening_time
        prev_ch: Optional[int] = None
        prev_genre = ""
        prev_prog_id: Optional[str] = None
        genre_streak = 0
        used_programs = set()
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
                prev_ch_id=prev_ch,
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

    def _local_search_window_size(self, schedule_len: int) -> int:
        if schedule_len <= 0:
            return 0

        window_size = max(2, round(schedule_len * 0.2))
        return min(window_size, 8, schedule_len)

    def _weakest_windows(self,
                         schedule: List[Schedule],
                         max_windows: int) -> List[Tuple[int, int, float]]:
        schedule_len = len(schedule)
        window_size = self._local_search_window_size(schedule_len)

        if window_size <= 0 or max_windows <= 0:
            return []

        windows: List[Tuple[int, int, float, int]] = []
        for start_idx in range(0, schedule_len - window_size + 1):
            window = schedule[start_idx:start_idx + window_size]
            window_score = sum(scheduled.fitness for scheduled in window)
            window_duration = sum(max(1, scheduled.end - scheduled.start) for scheduled in window)
            density = window_score / window_duration
            windows.append((start_idx, start_idx + window_size, density, window_score))

        windows.sort(key=lambda item: (item[2], item[3]))
        selected: List[Tuple[int, int, float]] = []

        for start_idx, end_idx, density, _ in windows:
            overlaps = any(start_idx < selected_end and end_idx > selected_start
                           for selected_start, selected_end, _ in selected)
            if overlaps:
                continue

            selected.append((start_idx, end_idx, density))
            if len(selected) >= max_windows:
                break

        return selected

    def _recalculate_schedule(self, schedule: List[Schedule]) -> Optional[Solution]:
        used_programs = set()
        recalculated: List[Schedule] = []
        total_score = 0
        prev_end = self.instance_data.opening_time
        prev_ch: Optional[int] = None
        prev_genre = ""
        genre_streak = 0

        for scheduled in schedule:
            if scheduled.start < prev_end or scheduled.end <= scheduled.start:
                return None

            if scheduled.unique_program_id in used_programs:
                return None

            prog_info = self.prog_by_id.get(scheduled.unique_program_id)
            if not prog_info:
                return None

            prog, ch_idx = prog_info
            channel_id = self.instance_data.channels[ch_idx].channel_id

            if scheduled.channel_id != channel_id:
                return None

            if scheduled.start < prog.start or scheduled.end > prog.end:
                return None

            if not self._channel_allowed(ch_idx, scheduled.start, scheduled.end):
                return None

            current_streak = genre_streak + 1 if prog.genre == prev_genre else 1
            if current_streak > self.instance_data.max_consecutive_genre:
                return None

            score = self._calc_score(prog, ch_idx, scheduled.start, scheduled.end, prev_ch)
            if score <= -999999:
                return None

            recalculated.append(Schedule(
                program_id=prog.program_id,
                channel_id=channel_id,
                start=scheduled.start,
                end=scheduled.end,
                fitness=score,
                unique_program_id=prog.unique_id
            ))
            total_score += score
            used_programs.add(prog.unique_id)
            prev_end = scheduled.end
            prev_ch = channel_id
            prev_genre = prog.genre
            genre_streak = current_streak

        return Solution(recalculated, total_score)

    def _state_before_index(self,
                            schedule: List[Schedule],
                            index: int) -> Tuple[Optional[int], str, int]:
        if index <= 0:
            return None, "", 0

        previous = schedule[index - 1]
        prog_info = self.prog_by_id.get(previous.unique_program_id)
        previous_genre = prog_info[0].genre if prog_info else ""
        genre_streak = 0

        for scheduled in reversed(schedule[:index]):
            scheduled_info = self.prog_by_id.get(scheduled.unique_program_id)
            scheduled_genre = scheduled_info[0].genre if scheduled_info else ""
            if scheduled_genre != previous_genre:
                break
            genre_streak += 1

        return previous.channel_id, previous_genre, genre_streak

    def _replacement_candidates_for_slot(self,
                                         schedule: List[Schedule],
                                         target_idx: int,
                                         max_candidates: int) -> List[Schedule]:
        target = schedule[target_idx]
        target_info = self.prog_by_id.get(target.unique_program_id)
        target_genre = target_info[0].genre if target_info else ""
        used_programs = {scheduled.unique_program_id for scheduled in schedule}
        used_programs.discard(target.unique_program_id)
        prev_ch, prev_genre, genre_streak = self._state_before_index(schedule, target_idx)
        next_start = (
            schedule[target_idx + 1].start
            if target_idx + 1 < len(schedule)
            else self.instance_data.closing_time
        )
        candidates: List[Tuple[float, Schedule]] = []

        for score, ch_idx, ch_id, prog, seg_start, seg_end in self._get_candidates(
            target.start,
            prev_ch,
            prev_genre,
            genre_streak,
            used_programs
        ):
            if prog.unique_id == target.unique_program_id:
                continue

            if seg_start < target.start or seg_end > next_start:
                continue

            replacement = Schedule(
                program_id=prog.program_id,
                channel_id=ch_id,
                start=seg_start,
                end=seg_end,
                fitness=score,
                unique_program_id=prog.unique_id
            )
            same_genre_bonus = 0.01 if prog.genre == target_genre else 0.0
            candidates.append((score + same_genre_bonus, replacement))

        candidates.sort(key=lambda item: item[0], reverse=True)
        return [replacement for _, replacement in candidates[:max_candidates]]

    def _window_state_priority(self, state, interval_end: int) -> float:
        local_score, time, *_ = state
        return local_score + max(0, interval_end - time) * self.avg_score_per_min

    def _repair_window_with_beam(self,
                                 solution: Solution,
                                 window_start: int,
                                 window_end: int,
                                 beam_width: int,
                                 candidate_limit: int) -> Optional[Solution]:
        schedule = solution.scheduled_programs
        if window_start >= window_end:
            return None

        interval_start = schedule[window_start].start
        interval_end = schedule[window_end - 1].end
        prefix = schedule[:window_start]
        suffix = schedule[window_end:]
        outside_used = {
            scheduled.unique_program_id
            for scheduled in prefix + suffix
        }
        prev_ch, prev_genre, genre_streak = self._state_before_index(schedule, window_start)
        initial = (
            0,
            interval_start,
            prev_ch,
            prev_genre,
            genre_streak,
            tuple(),
            frozenset(outside_used)
        )
        beam = [initial]
        best_candidate: Optional[Solution] = None
        best_score = solution.total_score
        max_steps = max(8, (window_end - window_start) * 4)
        steps = 0

        while beam and steps < max_steps:
            steps += 1
            next_beam = []

            for state in beam:
                local_score, time, prev_channel, current_genre, current_streak, local_tuple, used = state

                if time >= interval_end:
                    candidate = self._recalculate_schedule(prefix + list(local_tuple) + suffix)
                    if candidate and candidate.total_score > best_score:
                        best_candidate = candidate
                        best_score = candidate.total_score
                    continue

                candidates = self._get_candidates(time, prev_channel, current_genre, current_streak, used)
                candidates = [
                    candidate
                    for candidate in candidates
                    if candidate[4] >= interval_start and candidate[5] <= interval_end
                ]

                if not candidates:
                    idx = bisect.bisect_right(self.times, time)
                    if idx < len(self.times) and self.times[idx] < interval_end:
                        next_beam.append((
                            local_score,
                            self.times[idx],
                            prev_channel,
                            current_genre,
                            current_streak,
                            local_tuple,
                            used
                        ))
                    else:
                        candidate = self._recalculate_schedule(prefix + list(local_tuple) + suffix)
                        if candidate and candidate.total_score > best_score:
                            best_candidate = candidate
                            best_score = candidate.total_score
                    continue

                candidates.sort(
                    key=lambda candidate: candidate[0] + max(0, interval_end - candidate[5]) * self.avg_score_per_min,
                    reverse=True
                )

                for seg_score, ch_idx, ch_id, prog, seg_start, seg_end in candidates[:candidate_limit]:
                    local_schedule = Schedule(
                        program_id=prog.program_id,
                        channel_id=ch_id,
                        start=seg_start,
                        end=seg_end,
                        fitness=seg_score,
                        unique_program_id=prog.unique_id
                    )
                    new_streak = current_streak + 1 if prog.genre == current_genre else 1
                    next_beam.append((
                        local_score + seg_score,
                        seg_end,
                        ch_id,
                        prog.genre,
                        new_streak,
                        local_tuple + (local_schedule,),
                        used | {prog.unique_id}
                    ))

            if not next_beam:
                break

            next_beam.sort(
                key=lambda state: self._window_state_priority(state, interval_end),
                reverse=True
            )
            unique_beam = []
            seen = set()
            for state in next_beam:
                key = (state[1], state[2], state[4], tuple(s.unique_program_id for s in state[5]))
                if key in seen:
                    continue
                seen.add(key)
                unique_beam.append(state)
                if len(unique_beam) >= beam_width:
                    break

            beam = unique_beam

        return best_candidate

    def _best_window_replacement(self,
                                 solution: Solution,
                                 max_windows: int,
                                 targets_per_window: int,
                                 candidates_per_target: int) -> Tuple[Solution, Optional[Tuple[int, int, int]]]:
        best_solution = solution
        best_move: Optional[Tuple[int, int, int]] = None
        windows = self._weakest_windows(solution.scheduled_programs, max_windows)

        for window_start, window_end, _ in windows:
            window_indices = list(range(window_start, window_end))
            window_indices.sort(key=lambda idx: solution.scheduled_programs[idx].fitness)

            for target_idx in window_indices[:targets_per_window]:
                replacements = self._replacement_candidates_for_slot(
                    solution.scheduled_programs,
                    target_idx,
                    candidates_per_target
                )

                for replacement in replacements:
                    candidate_schedule = solution.scheduled_programs[:]
                    candidate_schedule[target_idx] = replacement
                    candidate = self._recalculate_schedule(candidate_schedule)

                    if candidate and candidate.total_score > best_solution.total_score:
                        best_solution = candidate
                        best_move = (window_start, window_end, target_idx)

            repaired = self._repair_window_with_beam(
                solution,
                window_start,
                window_end,
                beam_width=max(4, min(10, self.effective_candidate_cap)),
                candidate_limit=max(4, min(12, self.effective_candidate_cap))
            )
            if repaired and repaired.total_score > best_solution.total_score:
                best_solution = repaired
                best_move = (window_start, window_end, -1)

        return best_solution, best_move

    def _local_search(self, sol: Solution, max_iter: int = 50) -> Solution:
        """
        Window local search.

        ACO produces the global best once. After that, this method only tries
        small local replacement moves inside the weakest score-density windows.
        """
        if max_iter <= 0 or not sol.scheduled_programs:
            return sol

        best = self._recalculate_schedule(sol.scheduled_programs) or sol
        initial_score = best.total_score
        max_passes = max(1, min(max_iter, 8))
        max_windows = 2 if len(best.scheduled_programs) > 80 or self.n_channels > 300 else 3
        targets_per_window = 2
        candidates_per_target = min(10, self.effective_candidate_cap)

        for _ in range(max_passes):
            candidate, move = self._best_window_replacement(
                best,
                max_windows=max_windows,
                targets_per_window=targets_per_window,
                candidates_per_target=candidates_per_target
            )

            if candidate.total_score <= best.total_score:
                break

            if self.verbose:
                window_start, window_end, target_idx = move if move else (-1, -1, -1)
                move_label = "full-window repair" if target_idx == -1 else f"replacement at index {target_idx}"
                print(
                    f"  Window local search improved score "
                    f"{best.total_score} -> {candidate.total_score} "
                    f"in window [{window_start}, {window_end}) "
                    f"using {move_label}"
                )
            best = candidate

        if self.verbose and best.total_score == initial_score:
            print("  Window local search found no improving replacement")

        return best

    def _evaporate_pheromones(self):
        evaporation_factor = 1.0 - self.rho
        for prog_id in self.pheromones:
            evaporated = self.pheromones[prog_id] * evaporation_factor
            self.pheromones[prog_id] = min(self.tau_max, max(self.tau_min, evaporated))
        for edge_key in list(self.transition_pheromones.keys()):
            evaporated = self.transition_pheromones[edge_key] * evaporation_factor
            self.transition_pheromones[edge_key] = min(self.tau_max, max(self.tau_min, evaporated))
        for memory_key in list(self.time_transition_memory.keys()):
            evaporated = self.time_transition_memory[memory_key] * evaporation_factor
            if evaporated <= 1e-9:
                del self.time_transition_memory[memory_key]
            else:
                self.time_transition_memory[memory_key] = min(self.time_memory_max, evaporated)

    def _deposit_solution(self, solution: Solution, rank_weight: float, quality_multiplier: float = 1.0):
        solution_total = max(1.0, float(solution.total_score))
        prev_prog_id: Optional[str] = None
        prev_channel_id: Optional[int] = None

        for scheduled in solution.scheduled_programs:
            contribution = max(0.0, float(scheduled.fitness)) / solution_total
            prog_info = self.prog_by_id.get(scheduled.unique_program_id)
            next_genre = prog_info[0].genre if prog_info else ""
            if contribution <= 0:
                prev_prog_id = scheduled.unique_program_id
                prev_channel_id = scheduled.channel_id
                continue

            delta = rank_weight * quality_multiplier * contribution
            prog_id = scheduled.unique_program_id
            reinforced_node = self.pheromones.get(prog_id, self.tau0) + delta
            self.pheromones[prog_id] = min(self.tau_max, max(self.tau_min, reinforced_node))

            edge_key = self._transition_key(prev_prog_id, prog_id)
            reinforced_edge = self.transition_pheromones.get(edge_key, self.tau0) + delta
            self.transition_pheromones[edge_key] = min(self.tau_max, max(self.tau_min, reinforced_edge))

            memory_key = self._time_transition_key(
                scheduled.start,
                prev_channel_id,
                scheduled.channel_id,
                next_genre
            )
            reinforced_memory = self.time_transition_memory.get(memory_key, 0.0) + delta
            self.time_transition_memory[memory_key] = min(self.time_memory_max, reinforced_memory)

            prev_prog_id = prog_id
            prev_channel_id = scheduled.channel_id

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
            print(f"Exploitation probability: {self.exploitation_prob:.2f}, Window local search: {'on' if self.local_search_iterations > 0 else 'off'}")
            print("Elite carryover: on")
            print(f"Time bucket size: {self.time_bucket_size}, Memory strength: {self.memory_strength:.2f}")
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

            # Elitist ACO: carry the best solution found so far into the next
            # ranking step so the colony never forgets a strong path.
            if global_best.scheduled_programs:
                iteration_solutions.append(global_best)

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
