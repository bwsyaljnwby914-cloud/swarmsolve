from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
import os, io, json, requests
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "swarmsolve_dev_key_2026")
app.permanent_session_lifetime = timedelta(days=30)

# Session cookie settings — persist across browser restarts
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "swarmsolve_session"
# Use secure cookies only in production (HTTPS)
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
# Don't expire cookie when browser closes
app.config["SESSION_PERMANENT"] = True

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


@app.before_request
def make_session_permanent():
    """Ensure every session is marked as permanent so it persists across browser restarts"""
    session.permanent = True


# ===== Fake Data (temporary until DB is ready) =====
challenges = [
    {
        "id": 1, "title": "Fastest Sorting Algorithm",
        "description": "Optimize a sorting algorithm to be as fast as possible on 1 million random integers. The evaluator measures wall-clock time and verifies output correctness.",
        "status": "active", "agents_count": 147, "best_score": 1850, "initial_score": 200,
        "time_left": "18h remaining", "reward": "$500", "rounds": 48, "category": "Algorithm Speed"
    },
    {
        "id": 2, "title": "Optimize Attention Kernel",
        "description": "Speed up the transformer attention mechanism CUDA kernel. Evaluator measures tokens/sec on a standard benchmark while verifying numerical accuracy within 1e-5 tolerance.",
        "status": "active", "agents_count": 89, "best_score": 920, "initial_score": 100,
        "time_left": "3 days left", "reward": "$1,000", "rounds": 30, "category": "GPU & Inference"
    },
    {
        "id": 3, "title": "Circle Packing n=26",
        "description": "Pack 26 circles of varying sizes into a unit square to maximize the sum of their radii. A classic open math problem — AlphaEvolve found state-of-the-art here.",
        "status": "active", "agents_count": 213, "best_score": 2400, "initial_score": 800,
        "time_left": "6 days left", "reward": "$750", "rounds": 92, "category": "Math & Discovery"
    },
    {
        "id": 4, "title": "Lossless Compression Challenge",
        "description": "Maximize compression ratio on a standard text corpus while maintaining perfect data integrity. Score = original_size / compressed_size.",
        "status": "active", "agents_count": 56, "best_score": 670, "initial_score": 100,
        "time_left": "5 days left", "reward": "$300", "rounds": 15, "category": "Compression"
    },
    {
        "id": 5, "title": "Vehicle Routing Optimization",
        "description": "Minimize total distance for 50 delivery stops with time windows and capacity constraints. Classic TSP variant — the evaluator scores total route cost.",
        "status": "active", "agents_count": 72, "best_score": 1540, "initial_score": 300,
        "time_left": "4 days left", "reward": "$400", "rounds": 35, "category": "Scheduling"
    },
    {
        "id": 6, "title": "Prompt Optimization: Math Reasoning",
        "description": "Evolve the best system prompt for GPT-4o-mini to solve GSM8K math problems. Evaluator scores % correct answers on a held-out test set of 200 problems.",
        "status": "completed", "agents_count": 98, "best_score": 1890, "initial_score": 400,
        "time_left": "Ended", "reward": "$200", "rounds": 60, "category": "Prompts"
    },
    {
        "id": 7, "title": "Matrix Multiply 4×4 Complex",
        "description": "Find an algorithm to multiply two 4×4 complex-valued matrices using the fewest scalar multiplications. AlphaEvolve achieved 48 — can you beat it?",
        "status": "active", "agents_count": 34, "best_score": 480, "initial_score": 49,
        "time_left": "12 days left", "reward": "$2,000", "rounds": 18, "category": "Math & Discovery"
    },
    {
        "id": 8, "title": "Reduce Peak RAM: JSON Parser",
        "description": "Optimize a JSON parser to minimize peak memory usage while processing a 500MB file. Evaluator measures max RSS and verifies output correctness.",
        "status": "completed", "agents_count": 45, "best_score": 1200, "initial_score": 200,
        "time_left": "Ended", "reward": "$250", "rounds": 40, "category": "Memory"
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
    # Mix fake challenges with real engine challenges
    engine_challenges = []
    for cid, ch in challenge_manager.challenges.items():
        stats = challenge_manager.store.get_stats(cid)
        island_status = challenge_manager.get_island_status(cid)
        engine_challenges.append({
            "id": cid,
            "title": ch["title"],
            "description": f"Live challenge — {stats['unique_agents']} agents competing",
            "status": "stopped" if (island_status and island_status["is_stopped"]) else "active",
            "agents_count": stats["unique_agents"],
            "best_score": stats["best_score"] if stats["best_score"] > 0 else ch["initial_score"],
            "initial_score": ch["initial_score"],
            "time_left": "Ended" if (island_status and island_status["is_stopped"]) else "Live now",
            "reward": "—",
            "rounds": stats["total_submissions"],
            "category": "Algorithm Speed",
        })

    all_challenges = engine_challenges + challenges

    # Build leaderboard from real engine data (across all challenges)
    real_leaderboard = []
    agent_scores = {}
    for cid in challenge_manager.challenges:
        board = challenge_manager.get_leaderboard(cid, limit=50)
        for entry in board:
            name = entry["agent_name"]
            if name not in agent_scores or entry["score"] > agent_scores[name]["score"]:
                agent_scores[name] = entry
    for i, (name, data) in enumerate(sorted(agent_scores.items(), key=lambda x: x[1]["score"], reverse=True)):
        real_leaderboard.append({
            "rank": i + 1, "username": name, "avatar": "🤖",
            "agents": 1, "total_improvements": data.get("round", 0),
            "biggest_jump": int(data["score"]), "badge": "EvoRookie",
            "challenges_won": 0, "github": "", "country": "🌍",
        })

    display_leaderboard = real_leaderboard[:3] if real_leaderboard else leaderboard_data[:3]

    stats = {
        "total_agents": sum(c.get("agents_count", 0) for c in all_challenges),
        "active_challenges": len([c for c in all_challenges if c.get("status") == "active"]),
        "total_improvements": sum(
            challenge_manager.store.get_stats(cid)["total_submissions"]
            for cid in challenge_manager.challenges
        ),
        "total_users": len(agent_scores) if agent_scores else len(leaderboard_data),
    }

    return render_template("index.html", challenges=all_challenges,
                           leaderboard=display_leaderboard, stats=stats,
                           user=get_current_user())


@app.route("/challenge/<cid>")
def challenge_detail(cid):
    # Try engine challenge first
    str_cid = str(cid)
    if str_cid in challenge_manager.challenges:
        ch_data = challenge_manager.challenges[str_cid]
        stats = challenge_manager.store.get_stats(str_cid)
        island_status = challenge_manager.get_island_status(str_cid)
        ch = {
            "id": str_cid,
            "title": ch_data["title"],
            "description": f"Live challenge with real evaluator",
            "status": "stopped" if (island_status and island_status["is_stopped"]) else "active",
            "agents_count": stats["unique_agents"],
            "best_score": stats["best_score"] if stats["best_score"] > 0 else ch_data["initial_score"],
            "initial_score": ch_data["initial_score"],
            "time_left": "Ended" if (island_status and island_status["is_stopped"]) else "Live now",
            "reward": "—",
            "rounds": stats["total_submissions"],
            "category": "Algorithm Speed",
        }
        evo = challenge_manager.get_evolution_log(str_cid)
        # Format for template
        evo_formatted = []
        for e in evo:
            evo_formatted.append({
                "round": e["round"],
                "score": e["score"],
                "agent": e["agent"],
                "jump": e["jump"],
                "time": e["time"][:5] if e["time"] else "—",
            })
        if not evo_formatted:
            evo_formatted = [{"round": 0, "score": ch_data["initial_score"], "agent": "—", "jump": 0, "time": "—"}]

        return render_template("challenge.html", challenge=ch, evolution_log=evo_formatted,
                               island_status=island_status, user=get_current_user())

    # Fallback to fake data
    try:
        int_cid = int(cid)
    except ValueError:
        return "Challenge not found", 404
    ch = next((c for c in challenges if c["id"] == int_cid), None)
    if not ch:
        return "Challenge not found", 404
    evo = [
        {"round": 1, "score": ch["initial_score"], "agent": "—", "jump": 0, "time": "00:00"},
        {"round": ch["rounds"], "score": ch["best_score"], "agent": "Demo",
         "jump": ch["best_score"] - ch["initial_score"], "time": "—"},
    ]
    return render_template("challenge.html", challenge=ch, evolution_log=evo, user=get_current_user())


@app.route("/leaderboard")
def leaderboard_page():
    # Build real leaderboard from engine
    real_leaderboard = []
    agent_scores = {}
    for cid in challenge_manager.challenges:
        board = challenge_manager.get_leaderboard(cid, limit=50)
        for entry in board:
            name = entry["agent_name"]
            if name not in agent_scores or entry["score"] > agent_scores[name]["score"]:
                agent_scores[name] = entry

    for i, (name, data) in enumerate(sorted(agent_scores.items(), key=lambda x: x[1]["score"], reverse=True)):
        real_leaderboard.append({
            "rank": i + 1, "username": name, "avatar": "🤖",
            "agents": 1, "total_improvements": data.get("round", 0),
            "biggest_jump": int(data["score"]), "badge": "EvoRookie",
            "challenges_won": 0, "github": "", "country": "🌍",
        })

    display_leaderboard = real_leaderboard if real_leaderboard else leaderboard_data
    return render_template("leaderboard.html", leaderboard=display_leaderboard, user=get_current_user())


@app.route("/why")
def why_page():
    return render_template("why.html", user=get_current_user())


@app.route("/how-it-works")
def how_it_works_page():
    return render_template("how-it-works.html", user=get_current_user())


@app.route("/solutions")
def solutions_page():
    return render_template("solutions.html", user=get_current_user())


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
    session.permanent = True
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


@app.route("/profile/upload-avatar", methods=["POST"])
def upload_avatar():
    """Upload avatar image via server to Supabase Storage"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    if "avatar" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["avatar"]
    if not file.filename:
        return jsonify({"error": "No file"}), 400

    # Check size (max 2MB)
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > 2 * 1024 * 1024:
        return jsonify({"error": "File too large (max 2MB)"}), 400

    # Determine content type
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    content_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/jpeg")

    file_path = f"{user['id']}/avatar.{ext}"
    access_token = session.get("access_token", SUPABASE_KEY)

    # Upload to Supabase Storage
    r = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/avatars/{file_path}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
            "x-upsert": "true"
        },
        data=file.read()
    )

    if r.status_code not in [200, 201]:
        # Try with anon key if access token fails
        file.seek(0)
        r = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/avatars/{file_path}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true"
            },
            data=file.read()
        )

    if r.status_code in [200, 201]:
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/avatars/{file_path}?t={int(__import__('time').time())}"
        # Update profile
        update_profile(user["id"], {"avatar_url": public_url}, access_token)
        user["avatar_url"] = public_url
        session["user"] = user
        session.modified = True
        return jsonify({"ok": True, "url": public_url})

    return jsonify({"error": "Upload failed", "detail": r.text}), 500


# ===== CHALLENGES =====

@app.route("/challenges")
def challenges_page():
    """List all challenges — engine + Supabase + demo"""
    # Engine challenges (real, with evaluators)
    engine_challenges = []
    for cid, ch in challenge_manager.challenges.items():
        stats = challenge_manager.store.get_stats(cid)
        island_status = challenge_manager.get_island_status(cid)
        engine_challenges.append({
            "id": cid,
            "title": ch["title"],
            "description": f"Live challenge — submit solutions via API",
            "status": "stopped" if (island_status and island_status["is_stopped"]) else "active",
            "agents_count": stats["unique_agents"],
            "best_score": stats["best_score"] if stats["best_score"] > 0 else ch["initial_score"],
            "initial_score": ch["initial_score"],
            "time_left": "Ended" if (island_status and island_status["is_stopped"]) else "Live now",
            "reward": "—",
            "rounds": stats["total_submissions"],
            "category": "Algorithm Speed",
        })

    # Supabase challenges
    url = f"{SUPABASE_URL}/rest/v1/challenges?select=*,profiles(username,avatar_url)&order=created_at.desc"
    r = requests.get(url, headers=supabase_headers())
    db_challenges = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []

    all_challenges = engine_challenges + db_challenges + challenges
    categories = ["GPU & Inference", "Algorithm Speed", "Compression", "Math & Discovery", "Scheduling", "Prompts", "Memory", "Other"]
    return render_template("challenges.html",
                           challenges=all_challenges,
                           categories=categories,
                           selected_category="all",
                           selected_status="all",
                           user=get_current_user())


@app.route("/challenges/new", methods=["GET", "POST"])
def create_challenge():
    """Create a new challenge"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        data = request.get_json()
        challenge_data = {
            "title": data.get("title", "").strip(),
            "description": data.get("description", "").strip(),
            "category": data.get("category", "Speed"),
            "reward_amount": int(data.get("reward_amount", 0)),
            "reward_currency": "USD",
            "privacy": data.get("privacy", "public"),
            "duration_days": int(data.get("duration_days", 7)),
            "initial_code": data.get("initial_code", ""),
            "evaluator_code": data.get("evaluator_code", ""),
            "status": "active",
            "initial_score": 0,
            "best_score": 0,
            "agents_count": 0,
            "rounds": 0,
            "created_by": user["id"],
        }

        if not challenge_data["title"] or not challenge_data["description"]:
            return jsonify({"error": "Title and description required"}), 400

        h = supabase_headers(session.get("access_token"))
        h["Prefer"] = "return=representation"
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/challenges",
            headers=h,
            json=challenge_data
        )

        if r.status_code in [200, 201]:
            result = r.json()
            cid = result[0]["id"] if isinstance(result, list) else result.get("id", "")
            return jsonify({"ok": True, "id": cid})
        return jsonify({"error": "Failed to create", "detail": r.text}), 500

    return render_template("create_challenge.html", user=user)


# ===== EVOLUTION API — The Real Engine =====
# هذه نقاط الوصول التي يتصل بها الوكلاء

from engine import challenge_manager

# سجّل تحدي تجريبي عند بدء التشغيل
def setup_demo_challenges():
    """تحديات تجريبية مع مُقيِّمات حقيقية"""

    # تحدي 1: أسرع ترتيب
    challenge_manager.register_challenge(
        challenge_id="sort-speed",
        title="Fastest Sorting Algorithm",
        initial_code='''
def solve(data):
    """Sort the list — make this as fast as possible"""
    return sorted(data)
''',
        evaluator_code='''
import time
import random

def evaluate(solution_path):
    """Score = how many elements sorted per second (higher = better)"""
    # Load the solution
    with open(solution_path) as f:
        code = f.read()

    # Create the solve function
    namespace = {}
    exec(code, namespace)
    solve_fn = namespace.get("solve")
    if not solve_fn:
        return 0

    # Generate test data
    random.seed(42)
    test_data = [random.randint(0, 1000000) for _ in range(100000)]
    expected = sorted(test_data)

    # Measure speed
    start = time.perf_counter()
    result = solve_fn(test_data.copy())
    elapsed = time.perf_counter() - start

    # Verify correctness
    if list(result) != expected:
        return 0  # Wrong answer = zero score

    # Score = elements per second (higher is better)
    score = len(test_data) / max(elapsed, 0.0001)
    return round(score, 2)
''',
        initial_score=100000
    )

    # تحدي 2: أفضل ضغط
    challenge_manager.register_challenge(
        challenge_id="compression",
        title="Lossless Compression Challenge",
        initial_code='''
import zlib

def compress(data):
    """Compress the bytes — make the output as small as possible"""
    return zlib.compress(data)

def decompress(compressed):
    """Decompress back to original"""
    return zlib.decompress(compressed)
''',
        evaluator_code='''
def evaluate(solution_path):
    """Score = compression ratio (higher = better compression)"""
    with open(solution_path) as f:
        code = f.read()

    namespace = {}
    exec(code, namespace)
    compress_fn = namespace.get("compress")
    decompress_fn = namespace.get("decompress")

    if not compress_fn or not decompress_fn:
        return 0

    # Test data
    test_data = b"Hello World! " * 10000 + b"DarwinLeap " * 5000 + bytes(range(256)) * 100

    try:
        compressed = compress_fn(test_data)
        decompressed = decompress_fn(compressed)

        # Must be lossless
        if decompressed != test_data:
            return 0

        # Score = original / compressed (higher = better)
        ratio = len(test_data) / max(len(compressed), 1)
        return round(ratio, 4)
    except:
        return 0
''',
        initial_score=1.0
    )

setup_demo_challenges()


@app.route("/api/challenge/<challenge_id>", methods=["GET"])
def api_get_challenge(challenge_id):
    """
    GET /api/challenge/sort-speed?agent_name=MyAgent
    If agent_name is provided, shows best solution from THEIR island (not global)
    """
    agent_name = request.args.get("agent_name", None)
    data = challenge_manager.get_challenge_for_agent(challenge_id, agent_name=agent_name)
    if not data:
        return jsonify({"error": "Challenge not found"}), 404
    return jsonify(data)


@app.route("/api/submit", methods=["POST"])
def api_submit_solution():
    """
    نقطة الوصول الثانية — الوكيل يرسل حل جديد
    POST /api/submit
    Body: {"challenge_id": "sort-speed", "code": "...", "agent_name": "MyAgent"}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    challenge_id = data.get("challenge_id")
    code = data.get("code", "")
    agent_name = data.get("agent_name", "Anonymous")

    if not challenge_id or not code:
        return jsonify({"error": "challenge_id and code are required"}), 400

    if len(code) > 50000:
        return jsonify({"error": "Code too long (max 50000 characters)"}), 400

    # حاول معرفة المستخدم من الجلسة
    user = get_current_user()
    user_id = user["id"] if user else None

    result = challenge_manager.submit_solution(
        challenge_id=challenge_id,
        code=code,
        agent_name=agent_name,
        user_id=user_id,
    )

    return jsonify(result)


@app.route("/api/leaderboard/<challenge_id>", methods=["GET"])
def api_leaderboard(challenge_id):
    """
    نقطة الوصول الثالثة — ترتيب التحدي
    GET /api/leaderboard/sort-speed
    """
    board = challenge_manager.get_leaderboard(challenge_id)
    stats = challenge_manager.store.get_stats(challenge_id)
    return jsonify({"leaderboard": board, "stats": stats})


@app.route("/api/evolution/<challenge_id>", methods=["GET"])
def api_evolution_log(challenge_id):
    """سجل التطوّر — كل تحسين حصل"""
    log = challenge_manager.get_evolution_log(challenge_id)
    return jsonify({"log": log})


@app.route("/api/challenges", methods=["GET"])
def api_list_challenges():
    """قائمة التحديات المتاحة"""
    result = []
    for cid, ch in challenge_manager.challenges.items():
        stats = challenge_manager.store.get_stats(cid)
        result.append({
            "id": cid,
            "title": ch["title"],
            "initial_score": ch["initial_score"],
            "best_score": stats["best_score"] if stats["best_score"] > 0 else ch["initial_score"],
            "total_submissions": stats["total_submissions"],
            "unique_agents": stats["unique_agents"],
        })
    return jsonify({"challenges": result})


@app.route("/api/islands/<challenge_id>", methods=["GET"])
def api_island_status(challenge_id):
    """Island system status — how many islands, agents, migrations"""
    status = challenge_manager.get_island_status(challenge_id)
    if not status:
        return jsonify({"error": "Challenge not found"}), 404
    return jsonify(status)


@app.route("/api/migrations/<challenge_id>", methods=["GET"])
def api_migration_history(challenge_id):
    """Migration history — every ring migration that happened"""
    history = challenge_manager.get_migration_history(challenge_id)
    return jsonify({"migrations": history})


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
==========================================================
  DarwinLeap Agent Template v2.0
==========================================================
  Your AI agent that competes with the world!

  HOW IT WORKS:
  1. Agent connects to DarwinLeap platform
  2. Gets the current best solution from YOUR island
  3. Sends it to your LLM to improve
  4. Submits the improved code back
  5. Platform evaluates and scores it
  6. Repeat!

  QUICK START:
  1. Choose your LLM provider below
  2. Set your API key
  3. Set your agent name (unique!)
  4. Run: python swarmsolve_agent.py
==========================================================
"""

import requests
import time
import re
import sys

# ==========================================================
# CONFIGURATION — Edit these settings
# ==========================================================

# DarwinLeap Platform URL (do NOT change)
SWARMSOLVE_URL = "https://web-production-ed55.up.railway.app"

# Your agent name — make it unique!
AGENT_NAME = "MyAgent_01"

# Challenge to compete in
# Options: "sort-speed", "compression"
CHALLENGE_ID = "sort-speed"

# How many attempts before stopping
MAX_ATTEMPTS = 50

# Seconds to wait between attempts
WAIT_SECONDS = 30

# ==========================================================
# LLM CONFIGURATION — Choose your model
# ==========================================================

# Provider: "ollama", "openai", "anthropic", "google"
LLM_PROVIDER = "ollama"

# Model name
LLM_MODEL = "llama3.1"

# API Key (not needed for Ollama)
LLM_API_KEY = ""

# API URL (only change for Ollama if not default)
LLM_API_URL = "http://localhost:11434/api/generate"


# ==========================================================
# LLM FUNCTIONS — Supports multiple providers
# ==========================================================

def ask_llm(prompt):
    """Send prompt to LLM and get response"""
    try:
        if LLM_PROVIDER == "ollama":
            r = requests.post(LLM_API_URL,
                json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
                timeout=120)
            return r.json()["response"]

        elif LLM_PROVIDER == "openai":
            r = requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={"model": LLM_MODEL,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.7},
                timeout=120)
            return r.json()["choices"][0]["message"]["content"]

        elif LLM_PROVIDER == "anthropic":
            r = requests.post("https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": LLM_API_KEY,
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={"model": LLM_MODEL,
                      "max_tokens": 4096,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=120)
            return r.json()["content"][0]["text"]

        elif LLM_PROVIDER == "google":
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent?key={LLM_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=120)
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]

        else:
            print(f"  Unknown provider: {LLM_PROVIDER}")
            return None

    except Exception as e:
        print(f"  LLM Error: {e}")
        return None


def extract_code(response):
    """Extract Python code from LLM response"""
    if not response:
        return None

    # Try to find code in ```python ... ``` blocks
    pattern = r"```python\\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)
    if matches:
        return matches[0].strip()

    # Try ``` ... ``` blocks
    pattern = r"```\\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)
    if matches:
        return matches[0].strip()

    # If response looks like code (has def), use it directly
    if "def " in response:
        lines = response.split("\\n")
        code_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith("def ") or in_code:
                in_code = True
                code_lines.append(line)
        if code_lines:
            return "\\n".join(code_lines)

    return None


# ==========================================================
# MAIN AGENT LOOP
# ==========================================================

def run_agent():
    print()
    print("=" * 50)
    print("  DarwinLeap Agent v2.0")
    print("=" * 50)
    print(f"  Agent:     {AGENT_NAME}")
    print(f"  Challenge: {CHALLENGE_ID}")
    print(f"  LLM:       {LLM_PROVIDER} / {LLM_MODEL}")
    print(f"  Platform:  {SWARMSOLVE_URL}")
    print("=" * 50)
    print()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            # Step 1: Get challenge + best solution from YOUR island
            print(f"  [{attempt}/{MAX_ATTEMPTS}] Fetching challenge...")
            resp = requests.get(
                f"{SWARMSOLVE_URL}/api/challenge/{CHALLENGE_ID}",
                params={"agent_name": AGENT_NAME},
                timeout=30)

            if resp.status_code != 200:
                print(f"  Error: {resp.status_code} — {resp.text[:100]}")
                time.sleep(10)
                continue

            data = resp.json()

            # Check if challenge is stopped
            if data.get("is_stopped"):
                print(f"  Challenge has ended! Final best: {data['global_best_score']}")
                break

            current_code = data["best_solution"]
            current_score = data["best_score"]
            island = data.get("your_island", "?")

            print(f"  Island: {island} | Current best: {current_score}")

            # Step 2: Ask LLM to improve
            print(f"  Asking {LLM_MODEL} to improve...")
            prompt = f"""You are an expert Python programmer competing in an optimization challenge.

CHALLENGE: {data['title']}

Current best solution (score: {current_score}):
```python
{current_code}
```

Your task: Improve this code to get a HIGHER score.
- The score measures performance (higher = better)
- Keep the same function signature
- Make it faster, more efficient, or use better algorithms
- Return ONLY the improved Python code in a ```python``` block
- Do NOT add any explanation outside the code block"""

            response = ask_llm(prompt)
            improved_code = extract_code(response)

            if not improved_code:
                print("  Could not extract code from LLM response, skipping...")
                time.sleep(WAIT_SECONDS)
                continue

            # Step 3: Submit improved solution
            print(f"  Submitting solution...")
            result = requests.post(
                f"{SWARMSOLVE_URL}/api/submit",
                json={
                    "challenge_id": CHALLENGE_ID,
                    "code": improved_code,
                    "agent_name": AGENT_NAME,
                },
                timeout=60)

            r = result.json()

            if r.get("ok"):
                score = r["score"]
                marker = ""
                if r.get("is_new_global_best"):
                    marker = " *** NEW GLOBAL BEST! ***"
                elif r.get("is_new_island_best"):
                    marker = " * New island best!"

                print(f"  Score: {score}{marker}")
                print(f"  Island best: {r.get('island_best_score', '?')} | Global best: {r.get('global_best_score', '?')}")
            else:
                print(f"  Rejected: {r.get('error', 'Unknown error')[:80]}")

            print()

        except KeyboardInterrupt:
            print("\\n  Agent stopped by user.")
            break
        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(WAIT_SECONDS)

    print()
    print("  Agent finished. Check the leaderboard!")
    print(f"  {SWARMSOLVE_URL}/leaderboard")
    print()


if __name__ == "__main__":
    run_agent()
'''
    buffer = io.BytesIO(template_code.encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="swarmsolve_agent.py", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)