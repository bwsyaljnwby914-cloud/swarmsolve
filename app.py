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
    """List all challenges from Supabase + fake data"""
    # Fetch all from Supabase
    url = f"{SUPABASE_URL}/rest/v1/challenges?select=*,profiles(username,avatar_url)&order=created_at.desc"
    r = requests.get(url, headers=supabase_headers())
    db_challenges = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []

    all_challenges = db_challenges + challenges
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
    test_data = b"Hello World! " * 10000 + b"SwarmSolve " * 5000 + bytes(range(256)) * 100

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