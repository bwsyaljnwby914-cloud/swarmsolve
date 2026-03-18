from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
import os, io, json, requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "swarmsolve_dev_key_2026")

# ===== Supabase Config =====
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://bfvmheqcwaqojyidqceu.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJmdm1oZXFjd2Fxb2p5aWRxY2V1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4Mjc3ODAsImV4cCI6MjA4OTQwMzc4MH0._msqBmI8SrDMmzdc76c5f-MkP4owZENIEnqaCnxSHeg")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Content-Type": "application/json"
}

def supabase_headers(access_token=None):
    h = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if access_token:
        h["Authorization"] = f"Bearer {access_token}"
    else:
        h["Authorization"] = f"Bearer {SUPABASE_KEY}"
    return h


def get_profile(user_id, access_token=None):
    """Get user profile from Supabase"""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}&select=*",
        headers=supabase_headers(access_token)
    )
    if r.status_code == 200 and r.json():
        return r.json()[0]
    return None


def update_profile(user_id, data, access_token=None):
    """Update user profile in Supabase"""
    h = supabase_headers(access_token)
    h["Prefer"] = "return=representation"
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
        headers=h,
        json=data
    )
    return r.status_code == 200


def get_current_user():
    """Get current logged-in user from session"""
    return session.get("user")


# ===== Fake Data (temporary until DB is ready) =====
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

leaderboard_data = [
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


# ===== Routes =====

@app.route("/")
def home():
    active = [c for c in challenges if c["status"] == "active"]
    stats = {
        "total_agents": sum(c["agents_count"] for c in challenges),
        "active_challenges": len(active),
        "total_improvements": sum(u["total_improvements"] for u in leaderboard_data),
        "total_users": len(leaderboard_data)
    }
    return render_template("index.html", challenges=challenges, leaderboard=leaderboard_data[:3], stats=stats,
                           user=get_current_user())


@app.route("/challenge/<int:cid>")
def challenge_detail(cid):
    ch = next((c for c in challenges if c["id"] == cid), None)
    if not ch:
        return "Challenge not found", 404
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
    return render_template("challenge.html", challenge=ch, evolution_log=evo, user=get_current_user())


@app.route("/leaderboard")
def leaderboard_page():
    return render_template("leaderboard.html", leaderboard=leaderboard_data, user=get_current_user())


@app.route("/why")
def why_page():
    return render_template("why.html", user=get_current_user())


# ===== AUTH: Google Login via Supabase =====

@app.route("/login")
def login():
    """Redirect to Supabase Google OAuth"""
    # Build the redirect URL back to our app
    redirect_to = request.host_url.rstrip("/") + "/auth/callback"
    # Supabase OAuth URL
    auth_url = f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to={redirect_to}"
    return redirect(auth_url)


@app.route("/auth/callback")
def auth_callback():
    """Handle OAuth callback from Supabase"""
    # Supabase sends tokens as URL fragment (#), but we handle via query params
    # The actual token exchange happens client-side, so we render a page that extracts the hash
    return render_template("auth_callback.html")


@app.route("/auth/set-session", methods=["POST"])
def set_session():
    """Receive tokens from client-side JS and create server session"""
    data = request.get_json()
    access_token = data.get("access_token")
    if not access_token:
        return jsonify({"error": "No token"}), 400

    # Get user info from Supabase
    r = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {access_token}"}
    )
    if r.status_code != 200:
        return jsonify({"error": "Invalid token"}), 401

    user_data = r.json()
    user_id = user_data["id"]
    meta = user_data.get("user_metadata", {})

    # Get or create profile
    profile = get_profile(user_id, access_token)

    # Store in session
    session["user"] = {
        "id": user_id,
        "email": user_data.get("email", ""),
        "name": meta.get("full_name", ""),
        "avatar_url": meta.get("avatar_url", ""),
        "username": profile.get("username", "") if profile else "",
        "bio": profile.get("bio", "") if profile else "",
        "github": profile.get("github", "") if profile else "",
        "linkedin": profile.get("linkedin", "") if profile else "",
        "badge": profile.get("badge", "EvoRookie") if profile else "EvoRookie",
        "agents_count": profile.get("agents_count", 0) if profile else 0,
        "total_improvements": profile.get("total_improvements", 0) if profile else 0,
        "biggest_jump": profile.get("biggest_jump", 0) if profile else 0,
        "challenges_won": profile.get("challenges_won", 0) if profile else 0,
    }
    session["access_token"] = access_token
    session.modified = True

    is_new = not profile or not profile.get("username")
    return jsonify({"ok": True, "is_new": is_new})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/setup")
def setup():
    """Setup page for new users to complete their profile"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("setup.html", user=user, supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)


# ===== PROFILE =====

@app.route("/profile")
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    # Refresh profile from DB
    profile = get_profile(user["id"], session.get("access_token"))
    if profile:
        user.update({
            "username": profile.get("username", ""),
            "bio": profile.get("bio", ""),
            "github": profile.get("github", ""),
            "linkedin": profile.get("linkedin", ""),
            "avatar_url": profile.get("avatar_url", user.get("avatar_url", "")),
            "badge": profile.get("badge", "EvoRookie"),
            "agents_count": profile.get("agents_count", 0),
            "total_improvements": profile.get("total_improvements", 0),
            "biggest_jump": profile.get("biggest_jump", 0),
            "challenges_won": profile.get("challenges_won", 0),
        })
        session["user"] = user
        session.modified = True
    return render_template("profile.html", user=user, supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)


@app.route("/profile/update", methods=["POST"])
def profile_update():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    update_data = {}
    for field in ["username", "bio", "github", "linkedin", "full_name", "avatar_url"]:
        if field in data:
            update_data[field] = data[field]

    if update_data:
        update_data["updated_at"] = "now()"
        success = update_profile(user["id"], update_data, session.get("access_token"))
        if success:
            # Update session too
            for k, v in update_data.items():
                if k in user:
                    user[k] = v
            session["user"] = user
            session.modified = True
            return jsonify({"ok": True})
        return jsonify({"error": "Update failed"}), 500

    return jsonify({"error": "No data"}), 400


# ===== OTHER PAGES =====

@app.route("/new-agent")
def new_agent():
    if not get_current_user():
        return redirect(url_for("login"))
    return render_template("new_agent.html", user=get_current_user())


@app.route("/download-template")
def download_template():
    template_code = '''#!/usr/bin/env python3
"""
SwarmSolve Agent Template v1.0
Build your AI agent and compete with the world!

QUICK START:
1. Choose your LLM (see options below)
2. Set your API key
3. Run: python swarmsolve_agent.py
"""

import requests, time

SWARMSOLVE_URL = "https://swarmsolve.vercel.app/api"
AGENT_API_KEY = "YOUR_SWARMSOLVE_API_KEY"

LLM_PROVIDER = "ollama"
LLM_MODEL = "llama3.1"
LLM_API_URL = "http://localhost:11434/api/generate"
LLM_API_KEY = ""

CHALLENGE_ID = 1
MAX_ATTEMPTS = 100
WAIT_SECONDS = 60
AGENT_NAME = "MyAgent_01"

def ask_llm(prompt):
    if LLM_PROVIDER == "ollama":
        r = requests.post(LLM_API_URL, json={"model": LLM_MODEL, "prompt": prompt, "stream": False})
        return r.json()["response"]
    elif LLM_PROVIDER == "openai":
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}]})
        return r.json()["choices"][0]["message"]["content"]

def run_agent():
    print(f"  SwarmSolve Agent: {AGENT_NAME}")
    print(f"  LLM: {LLM_PROVIDER} / {LLM_MODEL}")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(f"{SWARMSOLVE_URL}/challenge/{CHALLENGE_ID}",
                headers={"Authorization": f"Bearer {AGENT_API_KEY}"})
            data = resp.json()
            improved = ask_llm(f"Improve this code:\\n{data['best_solution']}")
            result = requests.post(f"{SWARMSOLVE_URL}/submit",
                headers={"Authorization": f"Bearer {AGENT_API_KEY}"},
                json={"challenge_id": CHALLENGE_ID, "code": improved, "agent_name": AGENT_NAME})
            print(f"  [{attempt}] Score: {result.json().get('score', 0)}")
            time.sleep(WAIT_SECONDS)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_agent()
'''
    buffer = io.BytesIO(template_code.encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="swarmsolve_agent.py", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
