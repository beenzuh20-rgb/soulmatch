from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask import Flask, request, redirect, session, render_template
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "soulmatch_secret"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DB ---------------- #
def init_db():
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if "last_active" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN last_active TEXT")
    
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE, password TEXT,
        bio TEXT DEFAULT '', age TEXT DEFAULT '', gender TEXT DEFAULT '',
        location TEXT DEFAULT '', photo TEXT DEFAULT '', interests TEXT DEFAULT '',
        last_active TEXT
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS likes(id INTEGER PRIMARY KEY, liker INTEGER, liked INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, sender INTEGER, receiver INTEGER, message TEXT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY, reporter_id INTEGER, reported_id INTEGER, reason TEXT, details TEXT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS blocks(id INTEGER PRIMARY KEY, blocker_id INTEGER, blocked_id INTEGER, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(blocker_id, blocked_id))")
    
    conn.commit()
    conn.close()

init_db()

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
    if not last_active: return "Offline"
    try:
        last = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
        diff = datetime.utcnow() - last
        if diff < timedelta(minutes=2): return "🟢 Online"
        elif diff < timedelta(minutes=10): return f"Last seen {int(diff.seconds/60)} min ago"
        return "Offline"
    except:
        return "Offline"

def is_blocked(user_id, other_id):
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM blocks WHERE (blocker_id=? AND blocked_id=?) OR (blocker_id=? AND blocked_id=?)",
              (user_id, other_id, other_id, user_id))
    blocked = c.fetchone() is not None
    conn.close()
    return blocked

# ---------------- ROUTES ---------------- #
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
        return "Invalid login"
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if request.form.get("agree_terms") != "on":
            return "You must agree to the Terms and Conditions."
        conn = sqlite3.connect("dating.db")
        c = conn.cursor()
        hashed_pw = generate_password_hash(request.form["password"])
        c.execute("INSERT INTO users(username, password) VALUES(?,?)", 
                  (request.form["username"], hashed_pw))
        conn.commit()
        conn.close()
        return redirect("/login")
    return render_template("signup.html")

# ... (I will give you the rest of the routes + all template files in the next messages if needed)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
