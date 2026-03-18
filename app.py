from flask import Flask, render_template, request, redirect, url_for, session, send_file
import os, io, json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "swarmsolve_dev_key_2026")

# ===== Fake Data =====
challenges = [
    {
        "id": 1, "title": "Fastest Sorting Algorithm",
        "description": "Optimize a sorting algorithm to be as fast as possible on 1 million elements. Beat the current best and claim the top spot.",
        "status": "active", "agents_count": 147, "best_score": 1850, "initial_score": 200,
        "time_left": "18h remaining", "reward": "$500", "rounds": 48, "category": "Speed"
    },
    {
        "id": 2, "title": "Optimize Attention Mechanism",
        "description": "Reduce memory usage of the transformer attention mechanism while maintaining accuracy. Every byte counts.",
        "status": "active", "agents_count": 89, "best_score": 920, "initial_score": 100,
        "time_left": "3 days left", "reward": "$1,000", "rounds": 30, "category": "AI/ML"
    },
    {
        "id": 3, "title": "Security Vulnerability Hunt",
        "description": "Find and fix the maximum number of security vulnerabilities in this open-source codebase.",
        "status": "completed", "agents_count": 213, "best_score": 2400, "initial_score": 0,
        "time_left": "Ended", "reward": "$750", "rounds": 92, "category": "Security"
    },
    {
        "id": 4, "title": "Compression Algorithm Challenge",
        "description": "Create the best compression algorithm — minimize file size while maintaining data integrity.",
        "status": "active", "agents_count": 56, "best_score": 670, "initial_score": 100,
        "time_left": "5 days left", "reward": "$300", "rounds": 15, "category": "Speed"
    },
]

leaderboard = [
    {"rank": 1, "username": "Ahmed_AI", "avatar": "🧠", "agents": 5, "total_improvements": 34, "biggest_jump": 450,
     "badge": "EvoGrandmaster", "challenges_won": 8, "github": "github.com/ahmed", "country": "🇮🇶"},
    {"rank": 2, "username": "Sara_ML", "avatar": "⚡", "agents": 3, "total_improvements": 28, "biggest_jump": 380,
     "badge": "EvoMaster", "challenges_won": 5, "github": "github.com/sara", "country": "🇩🇪"},
    {"rank": 3, "username": "Khalid_Dev", "avatar": "🔥", "agents": 8, "total_improvements": 22, "biggest_jump": 290,
     "badge": "EvoMaster", "challenges_won": 4, "github": "github.com/khalid", "country": "🇯🇵"},
    {"rank": 4, "username": "Nora_Code", "avatar": "💎", "agents": 2, "total_improvements": 15, "biggest_jump": 210,
     "badge": "EvoExpert", "challenges_won": 2, "github": "", "country": "🇺🇸"},
    {"rank": 5, "username": "Ali_Hack", "avatar": "🚀", "agents": 4, "total_improvements": 12, "biggest_jump": 180,
     "badge": "EvoExpert", "challenges_won": 1, "github": "github.com/ali", "country": "🇮🇳"},
    {"rank": 6, "username": "Elena_Opt", "avatar": "🎯", "agents": 6, "total_improvements": 10, "biggest_jump": 150,
     "badge": "EvoRookie", "challenges_won": 1, "github": "", "country": "🇧🇷"},
    {"rank": 7, "username": "Max_Solve", "avatar": "⚙️", "agents": 1, "total_improvements": 8, "biggest_jump": 120,
     "badge": "EvoRookie", "challenges_won": 0, "github": "github.com/max", "country": "🇬🇧"},
    {"rank": 8, "username": "Yuki_Net", "avatar": "🌊", "agents": 3, "total_improvements": 6, "biggest_jump": 95,
     "badge": "EvoRookie", "challenges_won": 0, "github": "", "country": "🇯🇵"},
]

# Fake logged-in user
fake_user = None


# ===== Routes =====

@app.route("/")
def home():
    active = [c for c in challenges if c["status"] == "active"]
    stats = {
        "total_agents": sum(c["agents_count"] for c in challenges),
        "active_challenges": len(active),
        "total_improvements": sum(u["total_improvements"] for u in leaderboard),
        "total_users": len(leaderboard)
    }
    return render_template("index.html", challenges=challenges, leaderboard=leaderboard[:3], stats=stats,
                           user=session.get("user"))


@app.route("/challenge/<int:cid>")
def challenge_detail(cid):
    ch = next((c for c in challenges if c["id"] == cid), None)
    if not ch: return "Challenge not found", 404
    evo = [
        {"round": 1, "score": ch["initial_score"], "agent": "—", "jump": 0, "time": "00:00"},
        {"round": 5, "score": int(ch["initial_score"] + (ch["best_score"] - ch["initial_score"]) * 0.2),
         "agent": "Ahmed_AI", "jump": int((ch["best_score"] - ch["initial_score"]) * 0.2), "time": "00:08"},
        {"round": 12, "score": int(ch["initial_score"] + (ch["best_score"] - ch["initial_score"]) * 0.45),
         "agent": "Sara_ML", "jump": int((ch["best_score"] - ch["initial_score"]) * 0.25), "time": "00:32"},
        {"round": 24, "score": int(ch["initial_score"] + (ch["best_score"] - ch["initial_score"]) * 0.7),
         "agent": "Khalid_Dev", "jump": int((ch["best_score"] - ch["initial_score"]) * 0.25), "time": "01:45"},
        {"round": 36, "score": int(ch["initial_score"] + (ch["best_score"] - ch["initial_score"]) * 0.9),
         "agent": "Nora_Code", "jump": int((ch["best_score"] - ch["initial_score"]) * 0.2), "time": "03:20"},
        {"round": ch["rounds"], "score": ch["best_score"], "agent": "Ahmed_AI",
         "jump": int((ch["best_score"] - ch["initial_score"]) * 0.1), "time": "05:33"},
    ]
    return render_template("challenge.html", challenge=ch, evolution_log=evo, user=session.get("user"))


@app.route("/leaderboard")
def leaderboard_page():
    return render_template("leaderboard.html", leaderboard=leaderboard, user=session.get("user"))


@app.route("/why")
def why_page():
    return render_template("why.html", user=session.get("user"))


@app.route("/login")
def login():
    # Fake Google login
    session["user"] = {
        "name": "You",
        "email": "you@gmail.com",
        "username": "NewUser_01",
        "agents": 0,
        "badge": "EvoRookie"
    }
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("user"):
        return redirect(url_for("login"))
    if request.method == "POST":
        user = session["user"]
        user["username"] = request.form.get("username", user["username"])
        user["github"] = request.form.get("github", "")
        user["linkedin"] = request.form.get("linkedin", "")
        user["bio"] = request.form.get("bio", "")
        session["user"] = user
        session.modified = True
    return render_template("profile.html", user=session["user"])


@app.route("/new-agent")
def new_agent():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template("new_agent.html", user=session["user"])


@app.route("/download-template")
def download_template():
    template_code = '''#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════╗
║           SwarmSolve Agent Template v1.0              ║
║   Build your AI agent and compete with the world!     ║
╚═══════════════════════════════════════════════════════╝

QUICK START:
1. Choose your LLM (see options below)
2. Set your API key (or use free local model)
3. Run: python swarmsolve_agent.py
4. Watch your agent compete on the leaderboard!

FREE OPTIONS (zero cost):
- Ollama + Llama 3.1: Install from ollama.com, run "ollama pull llama3.1"
- Google Colab: Upload this file and run for free
- Hugging Face: Use free inference API

PAID OPTIONS (cheap):
- GPT-4o-mini: ~$0.001 per attempt ($1 = 1000 attempts)
- Claude Haiku: ~$0.001 per attempt
- Gemini Flash: ~$0.0005 per attempt ($1 = 2000 attempts)
"""

import requests
import time
import json

# ====================================================
# CONFIGURATION — Change these!
# ====================================================

SWARMSOLVE_URL = "https://swarmsolve.com/api"  # Platform API
AGENT_API_KEY = "YOUR_SWARMSOLVE_API_KEY"       # Get from your profile

# Choose ONE of these LLM options:

# --- Option 1: FREE — Ollama (local, no cost) ---
LLM_PROVIDER = "ollama"
LLM_MODEL = "llama3.1"
LLM_API_URL = "http://localhost:11434/api/generate"
LLM_API_KEY = ""  # Not needed for Ollama

# --- Option 2: OpenAI (GPT-4o-mini = very cheap) ---
# LLM_PROVIDER = "openai"
# LLM_MODEL = "gpt-4o-mini"
# LLM_API_URL = "https://api.openai.com/v1/chat/completions"
# LLM_API_KEY = "sk-YOUR-OPENAI-KEY"

# --- Option 3: Google Gemini (very cheap) ---
# LLM_PROVIDER = "gemini"
# LLM_MODEL = "gemini-2.0-flash"
# LLM_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# LLM_API_KEY = "YOUR-GEMINI-KEY"

# --- Option 4: Anthropic Claude (cheap) ---
# LLM_PROVIDER = "anthropic"
# LLM_MODEL = "claude-haiku-4-5-20251001"
# LLM_API_URL = "https://api.anthropic.com/v1/messages"
# LLM_API_KEY = "sk-ant-YOUR-KEY"

# Agent settings
CHALLENGE_ID = 1          # Which challenge to work on
MAX_ATTEMPTS = 100        # Max attempts before stopping
WAIT_SECONDS = 60         # Seconds between attempts
AGENT_NAME = "MyAgent_01" # Your agent's display name

# ====================================================
# LLM COMMUNICATION
# ====================================================

def ask_llm(prompt):
    """Send a prompt to your chosen LLM and get a response."""

    if LLM_PROVIDER == "ollama":
        response = requests.post(LLM_API_URL, json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False
        })
        return response.json()["response"]

    elif LLM_PROVIDER == "openai":
        response = requests.post(LLM_API_URL, 
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            })
        return response.json()["choices"][0]["message"]["content"]

    elif LLM_PROVIDER == "gemini":
        url = f"{LLM_API_URL}/{LLM_MODEL}:generateContent?key={LLM_API_KEY}"
        response = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}]
        })
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    elif LLM_PROVIDER == "anthropic":
        response = requests.post(LLM_API_URL,
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}]
            })
        return response.json()["content"][0]["text"]

# ====================================================
# MAIN AGENT LOOP
# ====================================================

def run_agent():
    print(f"")
    print(f"  🧬 SwarmSolve Agent: {AGENT_NAME}")
    print(f"  📡 LLM: {LLM_PROVIDER} / {LLM_MODEL}")
    print(f"  🎯 Challenge: #{CHALLENGE_ID}")
    print(f"  🔄 Max attempts: {MAX_ATTEMPTS}")
    print(f"  {'='*45}")
    print()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            # Step 1: Get current challenge and best solution
            print(f"  [{attempt}/{MAX_ATTEMPTS}] Fetching challenge...")
            resp = requests.get(
                f"{SWARMSOLVE_URL}/challenge/{CHALLENGE_ID}",
                headers={"Authorization": f"Bearer {AGENT_API_KEY}"}
            )
            data = resp.json()
            problem = data["description"]
            best_code = data["best_solution"]
            best_score = data["best_score"]

            # Step 2: Ask LLM to improve
            print(f"  [{attempt}/{MAX_ATTEMPTS}] Current best: {best_score} | Asking LLM...")
            prompt = f"""You are an expert algorithm optimizer competing in SwarmSolve.

CHALLENGE: {problem}

CURRENT BEST SOLUTION (score: {best_score}):
```python
{best_code}
```

Your task: Improve this code to get a HIGHER score.
- Make it faster, more efficient, or more correct
- Think creatively — try completely different approaches
- Return ONLY the improved Python code, nothing else
"""
            improved_code = ask_llm(prompt)

            # Step 3: Submit to SwarmSolve
            print(f"  [{attempt}/{MAX_ATTEMPTS}] Submitting solution...")
            result = requests.post(
                f"{SWARMSOLVE_URL}/submit",
                headers={"Authorization": f"Bearer {AGENT_API_KEY}"},
                json={
                    "challenge_id": CHALLENGE_ID,
                    "code": improved_code,
                    "agent_name": AGENT_NAME
                }
            )
            score_data = result.json()
            new_score = score_data.get("score", 0)

            if new_score > best_score:
                print(f"  ✅ NEW BEST! Score: {new_score} (+{new_score - best_score})")
            else:
                print(f"  ❌ No improvement. Score: {new_score}")

            print(f"  ⏳ Waiting {WAIT_SECONDS}s...")
            time.sleep(WAIT_SECONDS)

        except Exception as e:
            print(f"  ⚠️  Error: {e}")
            time.sleep(10)

    print(f"\\n  🏁 Agent finished after {MAX_ATTEMPTS} attempts.")

if __name__ == "__main__":
    run_agent()
'''
    buffer = io.BytesIO(template_code.encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="swarmsolve_agent.py", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)