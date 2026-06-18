from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask import Flask, request, redirect, session, render_template
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import secrets   # Added for password reset

app = Flask(__name__)
app.secret_key = "soulmatch_secret"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ---------------- #
def init_db():
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
   
    # Add last_active column if missing
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if "last_active" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN last_active TEXT")
    
    # Added for Forgot Password feature
    if "reset_token" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
    if "reset_expires" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN reset_expires TEXT")
   
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        bio TEXT DEFAULT '',
        age TEXT DEFAULT '',
        gender TEXT DEFAULT '',
        location TEXT DEFAULT '',
        photo TEXT DEFAULT '',
        interests TEXT DEFAULT '',
        last_active TEXT,
        reset_token TEXT,
        reset_expires TEXT
    )
    """)
    c.execute("CREATE TABLE IF NOT EXISTS likes(id INTEGER PRIMARY KEY AUTOINCREMENT, liker INTEGER, liked INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, sender INTEGER, receiver INTEGER, message TEXT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, reporter_id INTEGER, reported_id INTEGER, reason TEXT, details TEXT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS blocks(id INTEGER PRIMARY KEY AUTOINCREMENT, blocker_id INTEGER, blocked_id INTEGER, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(blocker_id, blocked_id))")
   
    conn.commit()
    conn.close()

init_db()

# Update last active
@app.before_request
def update_last_active():
    if "user_id" in session:
        conn = sqlite3.connect("dating.db")
        c = conn.cursor()
        c.execute("UPDATE users SET last_active = ? WHERE id = ?",
                 (datetime.utcnow().isoformat(), session["user_id"]))
        conn.commit()
        conn.close()

def get_online_status(last_active):
    if not last_active:
        return "Offline"
    try:
        last = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
        diff = datetime.utcnow() - last
        if diff < timedelta(minutes=2):
            return "🟢 Online"
        elif diff < timedelta(minutes=10):
            return f"Last seen {int(diff.seconds/60)} min ago"
        return "Offline"
    except:
        return "Offline"

def is_blocked(user_id, other_id):
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
    c.execute("""
        SELECT 1 FROM blocks
        WHERE (blocker_id=? AND blocked_id=?) OR (blocker_id=? AND blocked_id=?)
    """, (user_id, other_id, other_id, user_id))
    blocked = c.fetchone() is not None
    conn.close()
    return blocked

# ---------------- Forgot Password Routes ---------------- #
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username")
        conn = sqlite3.connect("dating.db")
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        user = c.fetchone()
        
        if user:
            token = secrets.token_urlsafe(32)
            expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
            
            c.execute("UPDATE users SET reset_token=?, reset_expires=? WHERE id=?", 
                     (token, expires, user[0]))
            conn.commit()
            conn.close()
            
            reset_link = f"https://{request.host}/reset_password/{token}"
            
            return render_template("forgot_password_success.html", reset_link=reset_link)
        
        conn.close()
        return render_template("forgot_password.html", error="Username not found")
    
    return render_template("forgot_password.html")
# ---------------- Existing Routes (Unchanged) ---------------- #
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/safety")
def safety():
    return render_template("safety.html")

@app.route("/guidelines")
def guidelines():
    return render_template("guidelines.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = sqlite3.connect("dating.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (request.form["username"],))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], request.form["password"]):
            session["user_id"] = user[0]
            return redirect("/profile")
        return "Invalid login credentials"
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if request.form.get("agree_terms") != "on":
            return "You must agree to the Terms and Conditions to create an account."
       
        conn = sqlite3.connect("dating.db")
        c = conn.cursor()
        hashed_pw = generate_password_hash(request.form["password"])
        try:
            c.execute("INSERT INTO users(username, password) VALUES(?,?)",
                      (request.form["username"], hashed_pw))
            conn.commit()
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists!"
    return render_template("signup.html")

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")
   
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
   
    if request.method == "POST":
        file_path = None
        if "photo" in request.files:
            file = request.files["photo"]
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
       
        c.execute("""UPDATE users SET bio=?, age=?, gender=?, location=?,
                    interests=?, photo=COALESCE(?, photo) WHERE id=?""", (
            request.form.get("bio"), request.form.get("age"),
            request.form.get("gender"), request.form.get("location"),
            request.form.get("interests"), file_path, session["user_id"]
        ))
        conn.commit()
   
    c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
    user = c.fetchone()
    conn.close()
   
    user_dict = {
        "id": user[0],
        "username": user[1],
        "bio": user[3],
        "age": user[4],
        "gender": user[5],
        "location": user[6],
        "photo": user[7],
        "interests": user[8],
        "last_active": user[9]
    }
   
    interests = [i.strip() for i in (user[8] or "").split(",") if i.strip()]
   
    return render_template("profile.html",
                         user=user_dict,
                         interests=interests,
                         get_online_status=get_online_status)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/swipe")
def swipe():
    if "user_id" not in session:
        return redirect("/login")
   
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
    c.execute("""
        SELECT * FROM users
        WHERE id != ?
        AND id NOT IN (SELECT blocked_id FROM blocks WHERE blocker_id = ?)
        AND id NOT IN (SELECT blocker_id FROM blocks WHERE blocked_id = ?)
        ORDER BY RANDOM() LIMIT 1
    """, (session["user_id"], session["user_id"], session["user_id"]))
    user = c.fetchone()
    conn.close()
   
    if not user:
        return redirect("/matches")
   
    user_dict = {
        "id": user[0], "username": user[1], "bio": user[3],
        "age": user[4], "gender": user[5], "photo": user[7],
        "last_active": user[9]
    }
   
    return render_template("swipe.html", user=user_dict, get_online_status=get_online_status)

@app.route("/like/<int:user_id>")
def like(user_id):
    if "user_id" not in session or is_blocked(session["user_id"], user_id):
        return redirect("/swipe")
   
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
    me = session["user_id"]
    c.execute("INSERT INTO likes(liker, liked) VALUES(?,?)", (me, user_id))
    c.execute("SELECT 1 FROM likes WHERE liker=? AND liked=?", (user_id, me))
    mutual = c.fetchone()
    conn.commit()
    conn.close()
   
    if mutual:
        return render_template("match.html")
    return redirect("/swipe")

@app.route("/matches")
def matches():
    if "user_id" not in session:
        return redirect("/login")
   
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
    c.execute("""
        SELECT u.* FROM users u
        JOIN likes l1 ON u.id = l1.liked
        JOIN likes l2 ON u.id = l2.liker
        WHERE l1.liker = ? AND l2.liked = ?
        AND u.id NOT IN (SELECT blocked_id FROM blocks WHERE blocker_id = ?)
        AND u.id NOT IN (SELECT blocker_id FROM blocks WHERE blocked_id = ?)
    """, (session["user_id"], session["user_id"], session["user_id"], session["user_id"]))
    rows = c.fetchall()
    conn.close()
   
    matches_list = []
    for row in rows:
        matches_list.append({
            "id": row[0],
            "username": row[1],
            "photo": row[7],
            "last_active": row[9]
        })
   
    return render_template("matches.html", matches=matches_list, get_online_status=get_online_status)

@app.route("/chat/<int:user_id>", methods=["GET", "POST"])
def chat(user_id):
    if "user_id" not in session:
        return redirect("/login")
   
    me = session["user_id"]
    if is_blocked(me, user_id):
        return "You have blocked this user or vice versa."
   
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
   
    if request.method == "POST":
        if "message" in request.form:
            msg = request.form.get("message", "").strip()
            if msg:
                c.execute("INSERT INTO messages(sender, receiver, message) VALUES(?,?,?)",
                         (me, user_id, msg))
                conn.commit()
        elif "report" in request.form:
            reason = request.form.get("reason")
            details = request.form.get("details", "")
            c.execute("INSERT INTO reports(reporter_id, reported_id, reason, details) VALUES(?,?,?,?)",
                     (me, user_id, reason, details))
            conn.commit()
            return "<h2>Report Submitted Successfully</h2><a href='/matches'>Back to Matches</a>"
        elif "block" in request.form:
            c.execute("INSERT OR IGNORE INTO blocks(blocker_id, blocked_id) VALUES(?,?)", (me, user_id))
            conn.commit()
            return "<h2>User Blocked</h2><a href='/matches'>Back to Matches</a>"
   
    c.execute("""
        SELECT * FROM messages
        WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
        ORDER BY id
    """, (me, user_id, user_id, me))
    messages = c.fetchall()
   
    c.execute("SELECT id, username, last_active FROM users WHERE id=?", (user_id,))
    other = c.fetchone()
    conn.close()
   
    other_dict = {"id": other[0], "username": other[1], "last_active": other[2]}
   
    return render_template("chat.html",
                         messages=messages,
                         other=other_dict,
                         current_user=me,
                         get_online_status=get_online_status)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
