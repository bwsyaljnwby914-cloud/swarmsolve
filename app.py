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


# ===== Routes =====

@app.route("/")
def home():
    # Real engine challenges only
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

    # Load user-created challenges from Supabase
    supabase_challenges = []
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/challenges?select=*&order=created_at.desc&limit=20",
            headers=supabase_headers(),
            timeout=5
        )
        if r.status_code == 200:
            for ch in r.json():
                if ch["id"] not in challenge_manager.challenges:
                    supabase_challenges.append({
                        "id": ch["id"],
                        "title": ch["title"],
                        "description": ch.get("description", ""),
                        "status": "stopped" if ch.get("is_stopped") else "active",
                        "agents_count": 0,
                        "best_score": ch.get("best_score", 0),
                        "initial_score": ch.get("initial_score", 0),
                        "time_left": "Ended" if ch.get("is_stopped") else "Live now",
                        "reward": f"${ch.get('reward_amount', 0)}" if ch.get("reward_amount") else "—",
                        "rounds": ch.get("total_rounds", 0),
                        "category": ch.get("category", "Other"),
                    })
    except:
        pass

    all_challenges = engine_challenges + supabase_challenges

    # Real stats only
    total_submissions = sum(
        challenge_manager.store.get_stats(cid)["total_submissions"]
        for cid in challenge_manager.challenges
    )

    # Count registered agents from Supabase
    registered_agents = 0
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/agents?select=id&is_active=eq.true",
            headers=supabase_headers(),
            timeout=5
        )
        if r.status_code == 200:
            registered_agents = len(r.json())
    except:
        pass

    stats = {
        "total_agents": registered_agents,
        "active_challenges": len(all_challenges),
        "total_improvements": total_submissions,
    }

    return render_template("index.html", challenges=all_challenges,
                           leaderboard=[], stats=stats,
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

    return "Challenge not found", 404


@app.route("/leaderboard")
def leaderboard_page():
    # Build leaderboard grouped by users from Supabase
    real_leaderboard = []

    try:
        # Get all solutions with user info
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/solutions?select=agent_name,score,user_id&score=gt.0&order=score.desc&limit=500",
            headers=supabase_headers(),
            timeout=10
        )
        solutions = r.json() if r.status_code == 200 else []

        # Get all agents with user info
        r2 = requests.get(
            f"{SUPABASE_URL}/rest/v1/agents?select=name,user_id,model&is_active=eq.true",
            headers=supabase_headers(),
            timeout=10
        )
        all_agents = r2.json() if r2.status_code == 200 else []

        # Get all profiles
        r3 = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?select=id,username,name,avatar_url,github",
            headers=supabase_headers(),
            timeout=10
        )
        profiles = {p["id"]: p for p in (r3.json() if r3.status_code == 200 else [])}

        # Group solutions by user_id
        user_best = {}  # user_id -> {best_score, agents: {name: score}}
        for sol in solutions:
            uid = sol.get("user_id")
            if not uid:
                # No user linked — show as individual agent
                uid = "anon_" + sol["agent_name"]
            if uid not in user_best:
                user_best[uid] = {"best_score": 0, "agents": {}, "total_submissions": 0}
            user_best[uid]["total_submissions"] += 1
            agent = sol["agent_name"]
            score = sol["score"]
            if agent not in user_best[uid]["agents"] or score > user_best[uid]["agents"][agent]:
                user_best[uid]["agents"][agent] = score
            if score > user_best[uid]["best_score"]:
                user_best[uid]["best_score"] = score

        # Build leaderboard entries
        sorted_users = sorted(user_best.items(), key=lambda x: x[1]["best_score"], reverse=True)

        for i, (uid, data) in enumerate(sorted_users[:50]):
            profile = profiles.get(uid, {})
            is_anon = uid.startswith("anon_")

            # Get user's registered agents
            user_agents = [a for a in all_agents if a.get("user_id") == uid] if not is_anon else []
            agent_names = list(data["agents"].keys())
            agent_scores = data["agents"]

            real_leaderboard.append({
                "rank": i + 1,
                "username": profile.get("username") or profile.get("name") or (uid.replace("anon_", "") if is_anon else "User"),
                "avatar_url": profile.get("avatar_url", ""),
                "avatar": "🤖" if is_anon else (profile.get("name", "U")[0].upper() if profile.get("name") else "U"),
                "agents": len(agent_names),
                "agent_list": [{"name": n, "score": agent_scores[n], "model": next((a["model"] for a in user_agents if a["name"] == n), "")} for n in sorted(agent_names, key=lambda x: agent_scores[x], reverse=True)],
                "best_score": int(data["best_score"]),
                "total_submissions": data["total_submissions"],
                "badge": "EvoMaster" if data["best_score"] > 10000000 else ("EvoExpert" if data["best_score"] > 1000000 else "EvoRookie"),
                "github": profile.get("github", ""),
                "country": "🌍",
            })
    except Exception as e:
        print(f"[LB] Error building leaderboard: {e}")

    # Fall back to engine data if Supabase has nothing
    if not real_leaderboard:
        agent_scores = {}
        for cid in challenge_manager.challenges:
            board = challenge_manager.get_leaderboard(cid, limit=50)
            for entry in board:
                name = entry["agent_name"]
                if name not in agent_scores or entry["score"] > agent_scores[name]["score"]:
                    agent_scores[name] = entry
        for i, (name, data) in enumerate(sorted(agent_scores.items(), key=lambda x: x[1]["score"], reverse=True)):
            real_leaderboard.append({
                "rank": i + 1, "username": name, "avatar": "🤖", "avatar_url": "",
                "agents": 1, "agent_list": [{"name": name, "score": int(data["score"]), "model": ""}],
                "best_score": int(data["score"]), "total_submissions": 1,
                "badge": "EvoRookie", "github": "", "country": "🌍",
            })

    display_leaderboard = real_leaderboard
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

    all_challenges = engine_challenges + db_challenges
    categories = ["GPU & Inference", "Algorithm Speed", "Compression", "Math & Discovery", "Scheduling", "Prompts", "Memory", "Other"]
    return render_template("challenges.html",
                           challenges=all_challenges,
                           categories=categories,
                           selected_category="all",
                           selected_status="all",
                           user=get_current_user())


@app.route("/challenges/new", methods=["GET", "POST"])
def create_challenge():
    """Create a new challenge with auto-built evaluator"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        data = request.get_json()
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        initial_code = data.get("initial_code", "").strip()
        metrics = data.get("metrics", ["speed"])
        weights = data.get("weights", {})
        custom_eval = data.get("evaluator_code", "").strip()
        test_data = data.get("test_data", "").strip()
        privacy = data.get("privacy", "public")
        category = data.get("category", "Other")
        duration_days = int(data.get("duration_days", 7))
        reward_amount = int(data.get("reward_amount", 0))

        if not title or not description:
            return jsonify({"error": "Title and description required"}), 400
        if not initial_code:
            return jsonify({"error": "Initial code is required"}), 400

        # Generate challenge ID
        import hashlib, time as _time
        cid = hashlib.md5(f"{title}{_time.time()}".encode()).hexdigest()[:12]

        # Auto-build evaluator from selected metrics
        if "custom" in metrics and custom_eval:
            evaluator_code = custom_eval
        else:
            evaluator_code = build_evaluator(metrics, weights, test_data)

        # Run evaluator once on initial code to get initial score
        initial_score = 0
        try:
            from engine import SafeEvaluator
            evaluator = SafeEvaluator(timeout_seconds=30)
            initial_score = evaluator.evaluate(initial_code, evaluator_code)
            if initial_score <= 0:
                initial_score = 1  # minimum score
        except Exception as e:
            print(f"[EVAL] Initial eval failed: {e}")
            initial_score = 1

        # Register in the engine (makes it live immediately)
        try:
            challenge_manager.register_challenge(
                challenge_id=cid,
                title=title,
                initial_code=initial_code,
                evaluator_code=evaluator_code,
                initial_score=initial_score,
            )
        except Exception as e:
            print(f"[ENGINE] Registration failed: {e}")
            return jsonify({"error": f"Engine error: {str(e)}"}), 500

        # Save to Supabase for persistence
        try:
            db_save_challenge(
                cid, title, initial_code, evaluator_code, initial_score,
                best_score=initial_score, best_agent=None,
            )
            # Also save full metadata
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/challenges?id=eq.{cid}",
                headers=supabase_headers(),
                json={
                    "description": description,
                    "category": category,
                    "privacy": privacy,
                    "duration_days": duration_days,
                    "reward_amount": reward_amount,
                    "owner_id": user["id"],
                    "metrics": metrics,
                    "weights": weights,
                    "test_data": test_data,
                },
                timeout=5
            )
        except Exception as e:
            print(f"[DB] Save challenge failed: {e}")

        return jsonify({"ok": True, "id": cid, "initial_score": initial_score})

    return render_template("create_challenge.html", user=user)


def build_evaluator(metrics, weights, test_data=""):
    """Auto-build evaluator code from selected metrics"""

    parts = []
    parts.append('import time')
    parts.append('import sys')
    parts.append('import tracemalloc')
    parts.append('')
    parts.append('def evaluate(solution_path):')
    parts.append('    """Auto-generated evaluator"""')
    parts.append('    with open(solution_path) as f:')
    parts.append('        code = f.read()')
    parts.append('')
    parts.append('    # Load the solution')
    parts.append('    namespace = {}')
    parts.append('    try:')
    parts.append('        exec(code, namespace)')
    parts.append('    except Exception as e:')
    parts.append('        return 0  # Code has errors')
    parts.append('')
    parts.append('    solve_fn = namespace.get("solve")')
    parts.append('    if not solve_fn:')
    parts.append('        return 0  # No solve function')
    parts.append('')

    # Build test data
    parts.append('    # Test data')
    if test_data:
        parts.append(f'    test_input = {repr(test_data)}')
    else:
        parts.append('    import random')
        parts.append('    random.seed(42)')
        parts.append('    test_input = [random.randint(0, 1000000) for _ in range(100000)]')

    parts.append('')
    parts.append('    scores = {}')
    parts.append('')

    # Speed metric
    if "speed" in metrics:
        parts.append('    # Speed: elements per second (higher = better)')
        parts.append('    try:')
        parts.append('        start = time.perf_counter()')
        parts.append('        result = solve_fn(test_input if not isinstance(test_input, str) else list(test_input))')
        parts.append('        elapsed = time.perf_counter() - start')
        parts.append('        n = len(test_input) if hasattr(test_input, "__len__") else 1000')
        parts.append('        scores["speed"] = n / max(elapsed, 0.0001)')
        parts.append('    except:')
        parts.append('        scores["speed"] = 0')
        parts.append('')

    # Memory metric
    if "memory" in metrics:
        parts.append('    # Memory: inverse peak RAM (less memory = higher score)')
        parts.append('    try:')
        parts.append('        tracemalloc.start()')
        parts.append('        result = solve_fn(test_input if not isinstance(test_input, str) else list(test_input))')
        parts.append('        current, peak = tracemalloc.get_traced_memory()')
        parts.append('        tracemalloc.stop()')
        parts.append('        scores["memory"] = 1000000000 / max(peak, 1)  # inverse')
        parts.append('    except:')
        parts.append('        scores["memory"] = 0')
        parts.append('        try: tracemalloc.stop()')
        parts.append('        except: pass')
        parts.append('')

    # Correctness metric
    if "correctness" in metrics:
        parts.append('    # Correctness: must match expected output')
        parts.append('    try:')
        parts.append('        result = solve_fn(test_input if not isinstance(test_input, str) else list(test_input))')
        if test_data:
            parts.append('        expected = test_input  # user provided test data')
        else:
            parts.append('        expected = sorted(test_input)')
        parts.append('        scores["correctness"] = 1.0 if list(result) == list(expected) else 0.0')
        parts.append('    except:')
        parts.append('        scores["correctness"] = 0')
        parts.append('')

    # Code size metric
    if "size" in metrics:
        parts.append('    # Code size: shorter code = higher score')
        parts.append('    code_len = len(code.strip())')
        parts.append('    scores["size"] = 100000 / max(code_len, 1)')
        parts.append('')

    # Compression metric
    if "compression" in metrics:
        parts.append('    # Compression ratio: smaller output = higher score')
        parts.append('    try:')
        parts.append('        compress_fn = namespace.get("compress")')
        parts.append('        decompress_fn = namespace.get("decompress")')
        parts.append('        if compress_fn and decompress_fn:')
        parts.append('            test_bytes = test_input.encode() if isinstance(test_input, str) else bytes(str(test_input), "utf-8")')
        parts.append('            compressed = compress_fn(test_bytes)')
        parts.append('            decompressed = decompress_fn(compressed)')
        parts.append('            if decompressed == test_bytes:')
        parts.append('                scores["compression"] = len(test_bytes) / max(len(compressed), 1)')
        parts.append('            else:')
        parts.append('                scores["compression"] = 0')
        parts.append('        else:')
        parts.append('            scores["compression"] = 0')
        parts.append('    except:')
        parts.append('        scores["compression"] = 0')
        parts.append('')

    # Accuracy metric
    if "accuracy" in metrics:
        parts.append('    # Accuracy: closer to expected = higher score')
        parts.append('    try:')
        parts.append('        result = solve_fn(test_input if not isinstance(test_input, str) else list(test_input))')
        parts.append('        scores["accuracy"] = 1.0  # placeholder — customize per challenge')
        parts.append('    except:')
        parts.append('        scores["accuracy"] = 0')
        parts.append('')

    # Scalability metric
    if "scalability" in metrics:
        parts.append('    # Scalability: performance on 10x data')
        parts.append('    try:')
        parts.append('        import random as _r')
        parts.append('        _r.seed(99)')
        parts.append('        big_input = [_r.randint(0, 1000000) for _ in range(1000000)]')
        parts.append('        start = time.perf_counter()')
        parts.append('        solve_fn(big_input)')
        parts.append('        elapsed = time.perf_counter() - start')
        parts.append('        scores["scalability"] = len(big_input) / max(elapsed, 0.0001)')
        parts.append('    except:')
        parts.append('        scores["scalability"] = 0')
        parts.append('')

    # Combine scores with weights
    parts.append('    # Combine scores')
    parts.append('    if not scores:')
    parts.append('        return 0')
    parts.append('')

    # If correctness is a metric, fail if incorrect
    if "correctness" in metrics:
        parts.append('    if scores.get("correctness", 1) == 0:')
        parts.append('        return 0  # Must be correct')
        parts.append('')

    parts.append('    # Apply weights')
    parts.append(f'    weights = {repr(weights)}')
    parts.append('    total_weight = sum(weights.values()) if weights else len(scores)')
    parts.append('    if total_weight == 0:')
    parts.append('        total_weight = 1')
    parts.append('')
    parts.append('    final_score = 0')
    parts.append('    for metric, value in scores.items():')
    parts.append('        if metric == "correctness":')
    parts.append('            continue  # already checked above')
    parts.append('        w = weights.get(metric, 100/len(scores)) / total_weight')
    parts.append('        final_score += value * w')
    parts.append('')
    parts.append('    return round(final_score, 2)')

    return '\n'.join(parts)


# ===== EVOLUTION API — The Real Engine =====
# هذه نقاط الوصول التي يتصل بها الوكلاء

from engine import challenge_manager

# ===== Supabase Persistence Layer =====

def db_save_solution(challenge_id, agent_name, code, score, island_id, user_id=None, error=None):
    """Save a solution to Supabase"""
    try:
        data = {
            "challenge_id": challenge_id,
            "agent_name": agent_name,
            "code": code[:50000],  # limit size
            "score": score,
            "island_id": island_id,
            "user_id": user_id,
            "error": error,
        }
        requests.post(
            f"{SUPABASE_URL}/rest/v1/solutions",
            headers=supabase_headers(),
            json=data,
            timeout=5
        )
    except Exception as e:
        print(f"[DB] Failed to save solution: {e}")


def db_save_challenge(challenge_id, title, initial_code, evaluator_code, initial_score,
                      best_score=0, best_agent=None, is_stopped=False, total_rounds=0):
    """Save or update challenge in Supabase"""
    try:
        data = {
            "id": challenge_id,
            "title": title,
            "initial_code": initial_code,
            "evaluator_code": evaluator_code,
            "initial_score": initial_score,
            "best_score": best_score,
            "best_agent": best_agent,
            "is_stopped": is_stopped,
            "total_rounds": total_rounds,
        }
        # Upsert (insert or update)
        requests.post(
            f"{SUPABASE_URL}/rest/v1/challenges",
            headers={**supabase_headers(), "Prefer": "resolution=merge-duplicates"},
            json=data,
            timeout=5
        )
    except Exception as e:
        print(f"[DB] Failed to save challenge: {e}")


def db_update_challenge_best(challenge_id, best_score, best_agent, total_rounds, is_stopped):
    """Update challenge best score"""
    try:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/challenges?id=eq.{challenge_id}",
            headers=supabase_headers(),
            json={
                "best_score": best_score,
                "best_agent": best_agent,
                "total_rounds": total_rounds,
                "is_stopped": is_stopped,
            },
            timeout=5
        )
    except Exception as e:
        print(f"[DB] Failed to update challenge: {e}")


def db_save_migration(challenge_id, from_island, to_island, count, best_score, trigger_type):
    """Save migration event"""
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/migrations_log",
            headers=supabase_headers(),
            json={
                "challenge_id": challenge_id,
                "from_island": from_island,
                "to_island": to_island,
                "solutions_count": count,
                "best_score": best_score,
                "trigger_type": trigger_type,
            },
            timeout=5
        )
    except Exception as e:
        print(f"[DB] Failed to save migration: {e}")


def db_load_solutions(challenge_id):
    """Load all solutions for a challenge from Supabase"""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/solutions?challenge_id=eq.{challenge_id}&select=agent_name,code,score,island_id&order=created_at.asc&limit=5000",
            headers=supabase_headers(),
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[DB] Failed to load solutions: {e}")
    return []


def db_load_challenges():
    """Load all challenges from Supabase"""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/challenges?select=*",
            headers=supabase_headers(),
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[DB] Failed to load challenges: {e}")
    return []

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

# ===== Load existing solutions from Supabase on startup =====
def reload_from_db():
    """Reload solutions from Supabase into engine memory"""
    print("[DB] Loading existing data from Supabase...")

    for cid in challenge_manager.challenges:
        solutions = db_load_solutions(cid)
        if solutions:
            print(f"[DB] Loaded {len(solutions)} solutions for {cid}")
            for sol in solutions:
                agent_name = sol.get("agent_name", "Unknown")
                island_id = sol.get("island_id", 0)
                score = sol.get("score", 0)
                code = sol.get("code", "")

                if score > 0 and code:
                    im = challenge_manager.island_managers.get(cid)
                    if im:
                        im.assign_agent_to_island(agent_name)
                        solution_data = {
                            "code": code,
                            "score": score,
                            "agent_name": agent_name,
                            "island_id": island_id,
                        }
                        if island_id not in im.islands:
                            im.islands[island_id] = []
                        im.islands[island_id].append(solution_data)

                        if score > im.global_best_score:
                            im.global_best_score = score

                        challenge_manager.store.add(cid, solution_data)

        # Upsert challenge to DB
        ch = challenge_manager.challenges[cid]
        im = challenge_manager.island_managers.get(cid)
        db_save_challenge(
            cid, ch["title"], ch["initial_code"], ch["evaluator_code"],
            ch["initial_score"],
            best_score=im.global_best_score if im and im.global_best_score > float("-inf") else 0,
        )

    print("[DB] Reload complete")

try:
    reload_from_db()
except Exception as e:
    print(f"[DB] Reload failed (first run?): {e}")


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
    Body: {"challenge_id": "sort-speed", "code": "...", "agent_name": "MyAgent", "api_key": "dl_xxx"}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    challenge_id = data.get("challenge_id")
    code = data.get("code", "")
    agent_name = data.get("agent_name", "Anonymous")
    api_key = data.get("api_key", "")

    if not challenge_id or not code:
        return jsonify({"error": "challenge_id and code are required"}), 400

    if len(code) > 50000:
        return jsonify({"error": "Code too long (max 50000 characters)"}), 400

    # Verify API key if provided
    user_id = None
    if api_key:
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/agents?description=eq.{api_key}&name=eq.{agent_name}&select=user_id,id",
                headers=supabase_headers(),
                timeout=5
            )
            agents = r.json() if r.status_code == 200 else []
            if agents:
                user_id = agents[0].get("user_id")
                # Update submission count
                agent_id = agents[0].get("id")
                try:
                    requests.patch(
                        f"{SUPABASE_URL}/rest/v1/agents?id=eq.{agent_id}",
                        headers=supabase_headers(),
                        json={"total_submissions": agents[0].get("total_submissions", 0) + 1 if "total_submissions" in agents[0] else 1},
                        timeout=3
                    )
                except:
                    pass
            else:
                return jsonify({"error": "Invalid API key or agent name mismatch"}), 401
        except Exception as e:
            print(f"[AUTH] Key verification error: {e}")
    else:
        # No API key — try session
        user = get_current_user()
        user_id = user["id"] if user else None

    result = challenge_manager.submit_solution(
        challenge_id=challenge_id,
        code=code,
        agent_name=agent_name,
        user_id=user_id,
    )

    # Save to Supabase (async-style, don't block response)
    try:
        island_id = result.get("island_id", 0)
        score = result.get("score", 0)
        error = result.get("error", None)
        db_save_solution(challenge_id, agent_name, code, score, island_id, user_id, error)

        # Update challenge best if improved
        if result.get("is_new_global_best"):
            im = challenge_manager.island_managers.get(challenge_id)
            if im:
                db_update_challenge_best(
                    challenge_id,
                    im.global_best_score,
                    agent_name,
                    im.round_counter,
                    im.is_stopped
                )
    except Exception as e:
        print(f"[DB] Persistence error: {e}")

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


@app.route("/api/agents", methods=["GET"])
def api_list_user_agents():
    """List current user's agents"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/agents?user_id=eq.{user['id']}&select=*&order=created_at.desc",
            headers=supabase_headers(),
            timeout=10
        )
        agents = r.json() if r.status_code == 200 else []
        return jsonify({"agents": agents, "max_agents": 10})
    except:
        return jsonify({"agents": [], "max_agents": 10})


@app.route("/api/agents", methods=["POST"])
def api_create_agent():
    """Create a new agent for the current user"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    name = data.get("name", "").strip()
    model = data.get("model", "ollama/llama3.1")

    if not name:
        return jsonify({"error": "Agent name is required"}), 400
    if len(name) > 30:
        return jsonify({"error": "Name too long (max 30 chars)"}), 400

    # Check agent limit (max 10)
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/agents?user_id=eq.{user['id']}&select=id",
            headers=supabase_headers(),
            timeout=10
        )
        existing = r.json() if r.status_code == 200 else []
        if len(existing) >= 10:
            return jsonify({"error": "Maximum 10 agents allowed"}), 400
    except:
        pass

    # Generate API key
    import hashlib, secrets
    api_key = "dl_" + secrets.token_hex(24)

    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/agents",
            headers={**supabase_headers(), "Prefer": "return=representation"},
            json={
                "name": name,
                "user_id": user["id"],
                "model": model,
                "description": api_key,  # Store API key in description field
                "is_active": True,
                "total_submissions": 0,
                "best_score": 0,
            },
            timeout=10
        )
        if r.status_code in [200, 201]:
            agent = r.json()
            if isinstance(agent, list):
                agent = agent[0]
            return jsonify({
                "ok": True,
                "agent": {
                    "id": agent.get("id"),
                    "name": name,
                    "model": model,
                    "api_key": api_key,
                }
            })
        else:
            detail = r.text
            if "duplicate" in detail.lower() or "unique" in detail.lower():
                return jsonify({"error": "Agent name already exists"}), 400
            return jsonify({"error": "Failed to create agent"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/<int:agent_id>", methods=["DELETE"])
def api_delete_agent(agent_id):
    """Delete an agent"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    try:
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/agents?id=eq.{agent_id}&user_id=eq.{user['id']}",
            headers=supabase_headers(),
            timeout=10
        )
        return jsonify({"ok": True})
    except:
        return jsonify({"error": "Failed to delete"}), 500


@app.route("/download-template")
def download_template():
    agent_name = request.args.get("agent", "MyAgent_01")
    api_key = request.args.get("key", "")

    template_code = '''#!/usr/bin/env python3
"""
==========================================================
  DarwinLeap Agent Template v3.0
==========================================================
  Your AI agent that competes with the world!

  HOW IT WORKS:
  1. Agent connects to DarwinLeap platform
  2. Gets the current best solution from YOUR island
  3. Sends it to your LLM to improve
  4. Submits the improved code back
  5. Platform evaluates and scores it
  6. Repeat!

  TO CUSTOMIZE:
  1. Change LLM_PROVIDER and LLM_MODEL below
  2. Add your LLM API key (if using paid model)
  3. Edit the PROMPT to guide your agent's strategy
  4. Run: python darwinleap_agent.py
==========================================================
"""

import requests
import time
import re
import sys

# ==========================================================
# YOUR AGENT (auto-configured — do NOT change these)
# ==========================================================

PLATFORM_URL = "https://web-production-ed55.up.railway.app"
AGENT_NAME = "__AGENT_NAME__"
API_KEY = "__API_KEY__"

# ==========================================================
# CHALLENGE — which challenge to compete in
# ==========================================================

CHALLENGE_ID = "sort-speed"   # Options: "sort-speed", "compression"
MAX_ATTEMPTS = 50             # Stop after this many attempts
WAIT_SECONDS = 30             # Wait between attempts

# ==========================================================
# LLM — Choose your model (THIS IS WHAT YOU CUSTOMIZE)
# ==========================================================

# Provider: "ollama", "openai", "anthropic", "google", "groq"
LLM_PROVIDER = "ollama"

# Model name
LLM_MODEL = "llama3.1"

# API Key for your LLM (not needed for Ollama)
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
    print(f"  Platform:  {PLATFORM_URL}")
    print("=" * 50)
    print()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            # Step 1: Get challenge + best solution from YOUR island
            print(f"  [{attempt}/{MAX_ATTEMPTS}] Fetching challenge...")
            resp = requests.get(
                f"{PLATFORM_URL}/api/challenge/{CHALLENGE_ID}",
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
                f"{PLATFORM_URL}/api/submit",
                json={
                    "challenge_id": CHALLENGE_ID,
                    "code": improved_code,
                    "agent_name": AGENT_NAME,
                    "api_key": API_KEY,
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
    print(f"  {PLATFORM_URL}/leaderboard")
    print()


if __name__ == "__main__":
    run_agent()
'''
    # Inject agent name and API key
    template_code = template_code.replace("__AGENT_NAME__", agent_name)
    template_code = template_code.replace("__API_KEY__", api_key)

    buffer = io.BytesIO(template_code.encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="darwinleap_agent.py", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)