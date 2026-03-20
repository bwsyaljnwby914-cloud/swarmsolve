"""
SwarmSolve Evolution Engine v2.0
================================
1. SafeEvaluator  — runs untrusted code safely, returns numeric score
2. IslandManager  — splits agents into islands, ring migration, auto-scaling
3. SolutionStore  — stores solutions per island with scoring and ranking
4. ChallengeManager — ties everything together
"""

import subprocess
import tempfile
import os
import sys
import time
import json
import hashlib
from datetime import datetime
from collections import defaultdict


# ============================================================
# 1. SAFE EVALUATOR
# ============================================================

class SafeEvaluator:

    def __init__(self, timeout_seconds=30):
        self.timeout = timeout_seconds

    def evaluate(self, solution_code, evaluator_code):
        safety_check = self._safety_check(solution_code)
        if not safety_check["ok"]:
            return safety_check

        with tempfile.TemporaryDirectory(prefix="swarm_eval_") as tmpdir:
            solution_path = os.path.join(tmpdir, "solution.py")
            evaluator_path = os.path.join(tmpdir, "evaluator.py")
            runner_path = os.path.join(tmpdir, "runner.py")
            result_path = os.path.join(tmpdir, "result.json")

            with open(solution_path, "w", encoding="utf-8") as f:
                f.write(solution_code)
            with open(evaluator_path, "w", encoding="utf-8") as f:
                f.write(evaluator_code)

            tmpdir_safe = tmpdir.replace("\\", "/")
            solution_safe = solution_path.replace("\\", "/")
            result_safe = result_path.replace("\\", "/")

            runner_code = f'''
import json, sys, os
sys.path.insert(0, r"{tmpdir_safe}")
try:
    from evaluator import evaluate
    score = evaluate(r"{solution_safe}")
    if not isinstance(score, (int, float)):
        result = {{"ok": False, "error": "Evaluator returned non-number: " + str(type(score))}}
    else:
        result = {{"ok": True, "score": float(score)}}
except Exception as e:
    result = {{"ok": False, "error": str(e)[:500]}}
with open(r"{result_safe}", "w", encoding="utf-8") as f:
    json.dump(result, f)
'''
            with open(runner_path, "w", encoding="utf-8") as f:
                f.write(runner_code)

            try:
                python_exe = sys.executable
                run_env = {
                    "PATH": os.environ.get("PATH", ""),
                    "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                    "TEMP": tmpdir, "TMP": tmpdir, "HOME": tmpdir,
                    "PYTHONIOENCODING": "utf-8",
                }
                proc = subprocess.run(
                    [python_exe, runner_path],
                    capture_output=True, timeout=self.timeout,
                    cwd=tmpdir, env=run_env,
                )
                if os.path.exists(result_path):
                    with open(result_path, encoding="utf-8") as f:
                        return json.load(f)
                else:
                    stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
                    return {"ok": False, "error": f"Execution failed: {stderr}"}
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": f"Timeout ({self.timeout}s)"}
            except Exception as e:
                return {"ok": False, "error": str(e)[:500]}

    def _safety_check(self, code):
        dangerous = [
            "os.system", "subprocess", "shutil.rmtree",
            "__import__('os')", "exec(", "eval(",
            "open('/etc", "open('/root", "open('/home",
            "requests.get", "requests.post", "urllib",
            "socket.", "http.client",
        ]
        code_lower = code.lower()
        for pattern in dangerous:
            if pattern.lower() in code_lower:
                return {"ok": False, "error": f"Blocked: code contains {pattern}"}
        return {"ok": True}


# ============================================================
# 2. ISLAND MANAGER — Ring topology, auto-scaling, auto-stop
# ============================================================

class IslandManager:

    SCALE_RULES = [
        (0, 1),      # < 10 agents = 1 island
        (10, 3),     # 10-49 = 3 islands
        (50, 5),     # 50-199 = 5 islands
        (200, 10),   # 200+ = 10 islands
    ]

    def __init__(self, challenge_id, migration_interval=20, migration_rate=0.1,
                 stagnation_limit=50):
        self.challenge_id = challenge_id
        self.migration_interval = migration_interval
        self.migration_rate = migration_rate
        self.stagnation_limit = stagnation_limit

        self.num_islands = 1
        self.islands = {0: []}
        self.agent_island_map = {}

        self.round_counter = 0
        self.rounds_since_improvement = 0
        self.global_best_score = float("-inf")
        self.migration_history = []
        self.is_stopped = False

    def _calculate_num_islands(self):
        num_agents = len(self.agent_island_map)
        result = 1
        for min_agents, num_islands in self.SCALE_RULES:
            if num_agents >= min_agents:
                result = num_islands
        return result

    def _maybe_rescale(self):
        needed = self._calculate_num_islands()
        if needed > self.num_islands:
            # Create new islands
            for i in range(self.num_islands, needed):
                self.islands[i] = []
            old_count = self.num_islands
            self.num_islands = needed

            # Redistribute ALL existing agents evenly across new island count
            all_agents = list(self.agent_island_map.keys())
            self.agent_island_map.clear()
            for idx, agent in enumerate(all_agents):
                self.agent_island_map[agent] = idx % self.num_islands

    def assign_agent_to_island(self, agent_name):
        if agent_name in self.agent_island_map:
            return self.agent_island_map[agent_name]

        self._maybe_rescale()

        island_counts = defaultdict(int)
        for aid in range(self.num_islands):
            island_counts[aid] = 0
        for assigned_island in self.agent_island_map.values():
            island_counts[assigned_island] += 1

        target = min(island_counts, key=island_counts.get)
        self.agent_island_map[agent_name] = target
        return target

    def add_solution(self, island_id, solution):
        if island_id not in self.islands:
            self.islands[island_id] = []
        self.islands[island_id].append(solution)

        self.round_counter += 1

        if solution["score"] > self.global_best_score:
            self.global_best_score = solution["score"]
            self.rounds_since_improvement = 0
        else:
            self.rounds_since_improvement += 1

        if self.rounds_since_improvement >= self.stagnation_limit:
            self.is_stopped = True

        if self.num_islands > 1 and self.round_counter % self.migration_interval == 0:
            self._do_migration()

    def _do_migration(self):
        """Ring migration: island i sends top solutions to island (i+1) % n"""
        if self.num_islands <= 1:
            return

        record = {
            "round": self.round_counter,
            "time": datetime.now().isoformat(),
            "transfers": [],
        }

        for i in range(self.num_islands):
            source = i
            target = (i + 1) % self.num_islands

            source_sols = self.islands.get(source, [])
            if not source_sols:
                continue

            sorted_sols = sorted(source_sols, key=lambda s: s["score"], reverse=True)
            num_migrate = max(1, int(len(sorted_sols) * self.migration_rate))
            migrants = sorted_sols[:num_migrate]

            target_codes = set(s["code"] for s in self.islands.get(target, []))
            added = 0
            for m in migrants:
                if m["code"] not in target_codes:
                    mcopy = dict(m)
                    mcopy["migrated_from"] = source
                    mcopy["migration_round"] = self.round_counter
                    if target not in self.islands:
                        self.islands[target] = []
                    self.islands[target].append(mcopy)
                    added += 1

            if added > 0:
                record["transfers"].append({
                    "from": source, "to": target,
                    "count": added, "best_score": migrants[0]["score"],
                })

        if record["transfers"]:
            self.migration_history.append(record)

    def get_best_for_island(self, island_id):
        sols = self.islands.get(island_id, [])
        if not sols:
            return None
        return max(sols, key=lambda s: s["score"])

    def get_global_best(self):
        all_sols = []
        for sols in self.islands.values():
            all_sols.extend(sols)
        if not all_sols:
            return None
        return max(all_sols, key=lambda s: s["score"])

    def get_island_stats(self):
        stats = []
        for i in range(self.num_islands):
            sols = self.islands.get(i, [])
            agents = [n for n, iid in self.agent_island_map.items() if iid == i]
            best = max(sols, key=lambda s: s["score"]) if sols else None
            stats.append({
                "island_id": i,
                "num_agents": len(agents),
                "num_solutions": len(sols),
                "best_score": best["score"] if best else 0,
                "best_agent": best["agent_name"] if best else None,
            })
        return stats

    def get_status(self):
        return {
            "num_islands": self.num_islands,
            "total_agents": len(self.agent_island_map),
            "total_rounds": self.round_counter,
            "global_best_score": self.global_best_score if self.global_best_score > float("-inf") else 0,
            "rounds_since_improvement": self.rounds_since_improvement,
            "is_stopped": self.is_stopped,
            "migrations_completed": len(self.migration_history),
            "island_stats": self.get_island_stats(),
        }


# ============================================================
# 3. SOLUTION STORE
# ============================================================

class SolutionStore:

    def __init__(self):
        self.all_solutions = {}

    def add_solution(self, challenge_id, code, score, agent_name, island_id=0, user_id=None):
        if challenge_id not in self.all_solutions:
            self.all_solutions[challenge_id] = []
        solution = {
            "id": hashlib.md5(code.encode()).hexdigest()[:12],
            "code": code, "score": score,
            "agent_name": agent_name, "island_id": island_id,
            "user_id": user_id,
            "time": datetime.now().isoformat(),
            "round": len(self.all_solutions[challenge_id]) + 1,
        }
        self.all_solutions[challenge_id].append(solution)
        return solution

    def get_best_solution(self, challenge_id):
        if challenge_id not in self.all_solutions or not self.all_solutions[challenge_id]:
            return None
        return max(self.all_solutions[challenge_id], key=lambda s: s["score"])

    def get_top_solutions(self, challenge_id, n=10):
        if challenge_id not in self.all_solutions:
            return []
        sorted_sols = sorted(self.all_solutions[challenge_id], key=lambda s: s["score"], reverse=True)
        return [
            {"rank": i+1, "agent_name": s["agent_name"], "score": s["score"],
             "island_id": s.get("island_id", 0), "round": s["round"], "time": s["time"]}
            for i, s in enumerate(sorted_sols[:n])
        ]

    def get_evolution_log(self, challenge_id, limit=30):
        if challenge_id not in self.all_solutions:
            return []
        log = []
        best_so_far = float("-inf")
        for s in self.all_solutions[challenge_id]:
            jump = max(0, s["score"] - best_so_far) if best_so_far > float("-inf") else 0
            if s["score"] > best_so_far:
                best_so_far = s["score"]
            log.append({
                "round": s["round"], "score": s["score"], "jump": round(jump, 2),
                "agent": s["agent_name"], "island_id": s.get("island_id", 0),
                "time": s["time"], "is_improvement": jump > 0,
            })
        return log[-limit:]

    def get_stats(self, challenge_id):
        if challenge_id not in self.all_solutions or not self.all_solutions[challenge_id]:
            return {"total_submissions": 0, "best_score": 0, "unique_agents": 0, "rounds": 0}
        sols = self.all_solutions[challenge_id]
        return {
            "total_submissions": len(sols),
            "best_score": max(s["score"] for s in sols),
            "unique_agents": len(set(s["agent_name"] for s in sols)),
            "rounds": len(sols),
        }


# ============================================================
# 4. CHALLENGE MANAGER
# ============================================================

class ChallengeManager:

    def __init__(self):
        self.evaluator = SafeEvaluator(timeout_seconds=30)
        self.store = SolutionStore()
        self.challenges = {}
        self.island_managers = {}

    def register_challenge(self, challenge_id, title, initial_code, evaluator_code,
                           initial_score=0, migration_interval=20, stagnation_limit=50):
        self.challenges[challenge_id] = {
            "id": challenge_id, "title": title,
            "initial_code": initial_code, "evaluator_code": evaluator_code,
            "initial_score": initial_score,
            "created_at": datetime.now().isoformat(),
        }
        self.island_managers[challenge_id] = IslandManager(
            challenge_id=challenge_id,
            migration_interval=migration_interval,
            stagnation_limit=stagnation_limit,
        )

    def get_challenge_for_agent(self, challenge_id, agent_name=None):
        if challenge_id not in self.challenges:
            return None

        ch = self.challenges[challenge_id]
        im = self.island_managers[challenge_id]

        island_id = None
        island_best = None
        if agent_name and not im.is_stopped:
            island_id = im.assign_agent_to_island(agent_name)
            island_best = im.get_best_for_island(island_id)

        global_best = self.store.get_best_solution(challenge_id)

        # Agent sees ISLAND best (not global) — this is isolation
        if island_best:
            visible_code = island_best["code"]
            visible_score = island_best["score"]
        elif global_best:
            visible_code = global_best["code"]
            visible_score = global_best["score"]
        else:
            visible_code = ch["initial_code"]
            visible_score = ch["initial_score"]

        status = im.get_status()
        return {
            "challenge_id": challenge_id,
            "title": ch["title"],
            "best_score": visible_score,
            "best_solution": visible_code,
            "global_best_score": global_best["score"] if global_best else ch["initial_score"],
            "initial_score": ch["initial_score"],
            "total_submissions": self.store.get_stats(challenge_id)["total_submissions"],
            "your_island": island_id,
            "num_islands": status["num_islands"],
            "is_stopped": status["is_stopped"],
        }

    def submit_solution(self, challenge_id, code, agent_name, user_id=None):
        if challenge_id not in self.challenges:
            return {"ok": False, "error": "Challenge not found"}

        ch = self.challenges[challenge_id]
        im = self.island_managers[challenge_id]

        if im.is_stopped:
            return {"ok": False, "error": f"Challenge stopped (no improvement for {im.stagnation_limit} rounds). Best: {im.global_best_score}"}

        island_id = im.assign_agent_to_island(agent_name)

        result = self.evaluator.evaluate(code, ch["evaluator_code"])
        if not result["ok"]:
            return {"ok": False, "error": result["error"], "agent_name": agent_name}

        score = result["score"]
        solution = self.store.add_solution(
            challenge_id=challenge_id, code=code, score=score,
            agent_name=agent_name, island_id=island_id, user_id=user_id,
        )

        im.add_solution(island_id, solution)

        global_best = self.store.get_best_solution(challenge_id)
        island_best = im.get_best_for_island(island_id)

        return {
            "ok": True, "score": score, "round": solution["round"],
            "island_id": island_id,
            "is_new_island_best": island_best and island_best["id"] == solution["id"],
            "is_new_global_best": global_best and global_best["id"] == solution["id"],
            "island_best_score": island_best["score"] if island_best else score,
            "global_best_score": global_best["score"] if global_best else score,
            "agent_name": agent_name,
            "is_stopped": im.is_stopped,
        }

    def get_leaderboard(self, challenge_id, limit=20):
        return self.store.get_top_solutions(challenge_id, limit)

    def get_evolution_log(self, challenge_id):
        return self.store.get_evolution_log(challenge_id)

    def get_island_status(self, challenge_id):
        if challenge_id not in self.island_managers:
            return None
        return self.island_managers[challenge_id].get_status()

    def get_migration_history(self, challenge_id):
        if challenge_id not in self.island_managers:
            return []
        return self.island_managers[challenge_id].migration_history


# Global instance
challenge_manager = ChallengeManager()