"""
DarwinLeap Docker Sandbox Evaluator
====================================
Runs untrusted code inside an isolated Docker container.
- No network access
- No filesystem access outside container
- Memory limited (256MB)
- CPU limited
- Auto-cleanup after execution
"""

import subprocess
import tempfile
import os
import json
import time


class DockerEvaluator:

    def __init__(self, timeout_seconds=30, memory_limit="256m", image_name="darwinleap-sandbox"):
        self.timeout = timeout_seconds
        self.memory_limit = memory_limit
        self.image_name = image_name

    def evaluate(self, solution_code, evaluator_code):
        """Run solution inside Docker sandbox, return {"ok": True/False, "score": float, "error": str}"""

        safety = self._safety_check(solution_code)
        if not safety["ok"]:
            return safety

        with tempfile.TemporaryDirectory(prefix="dl_eval_") as tmpdir:
            # Write files to temp directory
            solution_path = os.path.join(tmpdir, "solution.py")
            evaluator_path = os.path.join(tmpdir, "evaluator.py")
            runner_path = os.path.join(tmpdir, "runner.py")
            result_path = os.path.join(tmpdir, "result.json")

            with open(solution_path, "w", encoding="utf-8") as f:
                f.write(solution_code)
            with open(evaluator_path, "w", encoding="utf-8") as f:
                f.write(evaluator_code)

            runner_code = '''
import json, sys
sys.path.insert(0, "/sandbox")
try:
    from evaluator import evaluate
    score = evaluate("/sandbox/solution.py")
    if not isinstance(score, (int, float)):
        result = {"ok": False, "error": "Evaluator returned non-number: " + str(type(score))}
    else:
        result = {"ok": True, "score": float(score)}
except Exception as e:
    result = {"ok": False, "error": str(e)[:500]}
with open("/sandbox/result.json", "w", encoding="utf-8") as f:
    json.dump(result, f)
'''
            with open(runner_path, "w", encoding="utf-8") as f:
                f.write(runner_code)

            # Create empty result file (so Docker can write to it)
            with open(result_path, "w") as f:
                f.write("{}")

            try:
                # Run inside Docker container
                cmd = [
                    "docker", "run",
                    "--rm",                              # Auto-remove container
                    "--network", "none",                 # No network access
                    "--memory", self.memory_limit,        # Memory limit
                    "--cpus", "1",                        # CPU limit
                    "--pids-limit", "50",                 # Process limit
                    "--read-only",                        # Read-only filesystem
                    "--tmpfs", "/tmp:size=10m",           # Small tmp
                    "-v", f"{tmpdir}:/sandbox:rw",        # Mount code directory
                    "--workdir", "/sandbox",
                    self.image_name,
                    "python3", "/sandbox/runner.py"
                ]

                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=self.timeout + 10,  # Extra time for Docker overhead
                )

                if os.path.exists(result_path):
                    with open(result_path, encoding="utf-8") as f:
                        content = f.read().strip()
                        if content and content != "{}":
                            return json.loads(content)

                stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
                if proc.returncode != 0:
                    return {"ok": False, "error": f"Container error: {stderr}"}
                return {"ok": False, "error": "No result produced"}

            except subprocess.TimeoutExpired:
                # Kill container if timeout
                try:
                    subprocess.run(["docker", "kill", "--signal=KILL"],
                                   capture_output=True, timeout=5)
                except:
                    pass
                return {"ok": False, "error": f"Timeout ({self.timeout}s)"}
            except FileNotFoundError:
                return {"ok": False, "error": "Docker not found. Is Docker installed?"}
            except Exception as e:
                return {"ok": False, "error": str(e)[:500]}

    def _safety_check(self, code):
        """Basic pre-check before Docker (defense in depth)"""
        dangerous = [
            "os.system", "subprocess", "shutil.rmtree",
            "__import__('os')", "open('/etc", "open('/root",
            "requests.get", "requests.post", "urllib",
            "socket.", "http.client",
        ]
        code_lower = code.lower()
        for pattern in dangerous:
            if pattern.lower() in code_lower:
                return {"ok": False, "error": f"Blocked: code contains {pattern}"}
        return {"ok": True}

    @staticmethod
    def build_sandbox_image():
        """Build the sandbox Docker image (run once on server setup)"""
        dockerfile = '''FROM python:3.12-slim
RUN pip install --no-cache-dir numpy
RUN useradd -m -s /bin/bash sandbox
USER sandbox
WORKDIR /sandbox
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = os.path.join(tmpdir, "Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile)

            result = subprocess.run(
                ["docker", "build", "-t", "darwinleap-sandbox", tmpdir],
                capture_output=True, timeout=300,
            )
            if result.returncode == 0:
                print("[DockerEvaluator] Sandbox image built successfully!")
                return True
            else:
                err = result.stderr.decode("utf-8", errors="replace")
                print(f"[DockerEvaluator] Build failed: {err}")
                return False


# Quick test
if __name__ == "__main__":
    print("Building sandbox image...")
    DockerEvaluator.build_sandbox_image()

    print("\nTesting evaluator...")
    ev = DockerEvaluator(timeout_seconds=15)

    # Test 1: Simple working code
    result = ev.evaluate(
        solution_code="def solve():\n    return sorted([3,1,2])\n",
        evaluator_code="""
def evaluate(solution_path):
    exec(open(solution_path).read())
    result = solve()
    return 100.0 if result == [1,2,3] else 0.0
"""
    )
    print(f"Test 1 (should succeed): {result}")

    # Test 2: Dangerous code should be blocked
    result = ev.evaluate(
        solution_code="import os; os.system('rm -rf /')",
        evaluator_code="def evaluate(p): return 0"
    )
    print(f"Test 2 (should block): {result}")

    # Test 3: Timeout
    result = ev.evaluate(
        solution_code="import time; time.sleep(100)",
        evaluator_code="def evaluate(p): exec(open(p).read()); return 0"
    )
    print(f"Test 3 (should timeout): {result}")

    print("\nAll tests complete!")