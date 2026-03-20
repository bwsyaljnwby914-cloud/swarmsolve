#!/usr/bin/env python3
"""
SwarmSolve Engine v2 Test — Islands + Ring Migration + Auto-stop
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import ChallengeManager

def check(name, passed):
    print(f"  {'OK' if passed else 'FAIL'} {name}")
    return passed

def run():
    print("=" * 60)
    print("  SwarmSolve Engine v2 — Full Test")
    print("=" * 60)
    ok = True
    mgr = ChallengeManager()

    # -- Register challenge --
    print("\n[1] Register challenge...")
    mgr.register_challenge(
        challenge_id="test-sort", title="Test Sort",
        initial_code='def solve(data):\n    return sorted(data)\n',
        evaluator_code='''
import time, random
def evaluate(path):
    with open(path) as f: code = f.read()
    ns = {}
    exec(code, ns)
    fn = ns.get("solve")
    if not fn: return 0
    random.seed(42)
    data = [random.randint(0,100000) for _ in range(50000)]
    exp = sorted(data)
    t = time.perf_counter()
    res = fn(data.copy())
    elapsed = time.perf_counter() - t
    if list(res) != exp: return 0
    return round(len(data) / max(elapsed, 0.0001), 2)
''',
        initial_score=50000,
        migration_interval=5,  # migrate every 5 rounds (for testing)
        stagnation_limit=15,   # stop after 15 rounds no improvement
    )
    ok &= check("Challenge registered", "test-sort" in mgr.challenges)
    ok &= check("IslandManager created", "test-sort" in mgr.island_managers)

    # -- Submit from 12 different agents (should trigger 3 islands) --
    print("\n[2] Submit from 12 agents (auto-scale to 3 islands)...")
    agents = [f"Agent_{i:02d}" for i in range(12)]
    scores = {}
    for agent in agents:
        r = mgr.submit_solution("test-sort",
            'def solve(data):\n    return sorted(data)\n', agent)
        if r["ok"]:
            scores[agent] = r["score"]

    im = mgr.island_managers["test-sort"]
    ok &= check(f"Num islands = {im.num_islands} (expected 3)", im.num_islands == 3)
    ok &= check(f"All 12 agents assigned", len(im.agent_island_map) == 12)

    # Check distribution
    island_counts = {0: 0, 1: 0, 2: 0}
    for iid in im.agent_island_map.values():
        island_counts[iid] = island_counts.get(iid, 0) + 1
    print(f"     Distribution: {dict(island_counts)}")
    ok &= check("Balanced (4 per island)", all(c == 4 for c in island_counts.values()))

    # -- Check island isolation --
    print("\n[3] Island isolation...")
    # Agent_00 is on island X, Agent_04 is on island Y (different)
    island_a = im.agent_island_map["Agent_00"]
    island_b = im.agent_island_map["Agent_04"]
    data_a = mgr.get_challenge_for_agent("test-sort", "Agent_00")
    data_b = mgr.get_challenge_for_agent("test-sort", "Agent_04")
    ok &= check(f"Agent_00 sees island {data_a['your_island']}", data_a["your_island"] == island_a)
    ok &= check(f"Agent_04 sees island {data_b['your_island']}", data_b["your_island"] == island_b)

    # -- Submit more to trigger migration (need round 15 = 3rd multiple of 5) --
    print("\n[4] Submit more to trigger migration...")
    for i in range(8):  # 12 + 8 = 20 rounds total, migrations at 5, 10, 15, 20
        agent = agents[i % len(agents)]
        mgr.submit_solution("test-sort",
            f'def solve(data):\n    data.sort()  # v2-{agent}-{i}\n    return data\n', agent)

    ok &= check(f"Total rounds = {im.round_counter}", im.round_counter == 20)
    num_migrations = len(im.migration_history)
    print(f"     Migrations completed: {num_migrations}")
    ok &= check("At least 1 migration happened", num_migrations >= 1)

    # Show migration details
    for mig in im.migration_history:
        for t in mig["transfers"]:
            print(f"     Round {mig['round']}: Island {t['from']} -> Island {t['to']} ({t['count']} solutions, best={t['best_score']})")

    # -- Check ring topology (each island sends only to next) --
    print("\n[5] Ring topology check...")
    ring_correct = True
    for mig in im.migration_history:
        for t in mig["transfers"]:
            expected_target = (t["from"] + 1) % im.num_islands
            if t["to"] != expected_target:
                ring_correct = False
                print(f"     WRONG: Island {t['from']} sent to {t['to']}, expected {expected_target}")
    ok &= check("All migrations follow ring (i -> i+1)", ring_correct)

    # -- Island stats --
    print("\n[6] Island stats...")
    stats = im.get_island_stats()
    for s in stats:
        print(f"     Island {s['island_id']}: {s['num_agents']} agents, {s['num_solutions']} solutions, best={s['best_score']}")
    ok &= check("3 islands reported", len(stats) == 3)

    # -- Leaderboard includes island_id --
    print("\n[7] Leaderboard with island info...")
    board = mgr.get_leaderboard("test-sort", limit=5)
    ok &= check("Leaderboard not empty", len(board) > 0)
    ok &= check("Has island_id field", "island_id" in board[0])
    for entry in board[:3]:
        print(f"     #{entry['rank']}: {entry['agent_name']} — {entry['score']} (island {entry['island_id']})")

    # -- Auto-stop test --
    print("\n[8] Auto-stop after stagnation...")
    # Submit identical solutions to trigger stagnation
    for i in range(20):
        if im.is_stopped:
            break
        mgr.submit_solution("test-sort",
            'def solve(data):\n    return sorted(data)\n', "StaleAgent")

    print(f"     Rounds since improvement: {im.rounds_since_improvement}")
    print(f"     Is stopped: {im.is_stopped}")
    ok &= check("Auto-stopped after stagnation", im.is_stopped)

    # Verify new submissions are rejected
    r = mgr.submit_solution("test-sort",
        'def solve(data):\n    return sorted(data)\n', "LateAgent")
    ok &= check("New submission rejected", not r["ok"])
    print(f"     Rejection message: {r['error'][:60]}...")

    # -- Dangerous code still blocked --
    print("\n[9] Safety check still works...")
    # Register fresh challenge for this test
    mgr.register_challenge("test-safe", "Safety Test",
        'def solve(): return 1\n',
        'def evaluate(p): return 1\n', 1)
    r = mgr.submit_solution("test-safe",
        'import os\nos.system("rm -rf /")\ndef solve(): return 1', "Hacker")
    ok &= check("Dangerous code blocked", not r["ok"])

    # -- Status endpoint --
    print("\n[10] Full status endpoint...")
    status = mgr.get_island_status("test-sort")
    ok &= check("Status has num_islands", "num_islands" in status)
    ok &= check("Status has migrations_completed", "migrations_completed" in status)
    ok &= check("Status has is_stopped", status["is_stopped"] == True)
    print(f"     Total agents: {status['total_agents']}")
    print(f"     Total rounds: {status['total_rounds']}")
    print(f"     Global best: {status['global_best_score']}")
    print(f"     Migrations: {status['migrations_completed']}")

    # -- Final --
    print("\n" + "=" * 60)
    if ok:
        print("  ALL TESTS PASSED — Engine v2 with Islands works correctly")
    else:
        print("  SOME TESTS FAILED — check above")
    print("=" * 60)
    return ok

if __name__ == "__main__":
    sys.exit(0 if run() else 1)