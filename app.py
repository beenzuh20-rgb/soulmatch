import os
from flask import Flask, request, redirect, session, render_template, render_template_string
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "soulmatch_secret"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DB ---------------- #

def init_db():
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()

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
        interests TEXT DEFAULT ''
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS likes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        liker INTEGER,
        liked INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender INTEGER,
        receiver INTEGER,
        message TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- UI ---------------- #

base_css = """
<style>
body{
    margin:0;
    font-family:Segoe UI;
    background:url('https://images.unsplash.com/photo-1518199266791-5375a83190b7?auto=format&fit=crop&w=1500&q=80');
    background-size:cover;
    background-position:center;
}

.overlay{
    background:rgba(0,0,0,0.6);
    min-height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    padding:20px;
}

.glass{
    width:420px;
    background:rgba(255,255,255,0.15);
    backdrop-filter:blur(15px);
    border-radius:20px;
    padding:25px;
    color:white;
    box-shadow:0 10px 40px rgba(0,0,0,0.3);
}

input, textarea{
    width:100%;
    padding:10px;
    margin:6px 0;
    border:none;
    border-radius:10px;
}

button{
    width:100%;
    padding:12px;
    border:none;
    border-radius:12px;
    background:#ff4b6e;
    color:white;
    cursor:pointer;
    font-size:15px;
    display:flex;
    align-items:center;
    justify-content:center;
    gap:8px;
    transition:0.2s;
}

button:hover{
    transform:scale(1.03);
    opacity:0.9;
}
a{color:white;text-decoration:none}

img{
    width:100%;
    border-radius:15px;
}
</style>
"""

# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("home.html")

# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = sqlite3.connect("dating.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (request.form["username"], request.form["password"]))

        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/profile")

        return "Invalid login"

    return render_template_string(base_css + """
<div class="overlay">
<div class="glass">
<h2>Login</h2>
<form method="post">
<input name="username">
<input name="password" type="password">
<button>Login</button>
</form>
</div>
</div>
""")

# ---------------- SIGNUP ---------------- #

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        conn = sqlite3.connect("dating.db")
        c = conn.cursor()

        c.execute("INSERT INTO users(username,password) VALUES(?,?)",
                  (request.form["username"], request.form["password"]))

        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template_string(base_css + """
<div class="overlay">
<div class="glass">
<h2>Signup</h2>
<form method="post">
<input name="username">
<input name="password" type="password">
<button>Create</button>
</form>
</div>
</div>
""")

# ---------------- PROFILE ---------------- #

@app.route("/profile", methods=["GET","POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("dating.db")
    c = conn.cursor()

    if request.method == "POST":
        file_path = None

        if "photo" in request.files:
            file = request.files["photo"]
            if file.filename != "":
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)

        c.execute("""
        UPDATE users SET
        bio=?, age=?, gender=?, location=?, interests=?,
        photo=COALESCE(?, photo)
        WHERE id=?
        """, (
            request.form["bio"],
            request.form["age"],
            request.form["gender"],
            request.form["location"],
            request.form["interests"],
            file_path,
            session["user_id"]
        ))

        conn.commit()

    c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
    user = c.fetchone()
    conn.close()

    return render_template_string(base_css + """
<div class="overlay">
<div class="glass">

<h2>My Profile</h2>

{% if user[7] %}
<img src="{{user[7]}}">
{% endif %}

<p><b>{{user[1]}}</b></p>
<p>Age: {{user[4]}}</p>
<p>Gender: {{user[5]}}</p>
<p>Location: {{user[6]}}</p>
<p>Interests: {{user[8]}}</p>

<form method="post" enctype="multipart/form-data">
<input name="age" placeholder="Age">
<input name="gender" placeholder="Gender">
<input name="location" placeholder="Location">
<input name="interests" placeholder="Interests">
<textarea name="bio" placeholder="Bio"></textarea>

<input type="file" name="photo">

<button>Save</button>
</form>

<br>
<a href="/swipe">Swipe</a> |
<a href="/matches">Matches</a> |
<a href="/logout">Logout</a>

</div>
</div>
""", user=user)

# ---------------- LOGOUT (FIXED) ---------------- #

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- SWIPE ---------------- #

@app.route("/swipe")
def swipe():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("dating.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE id != ? LIMIT 1",
              (session["user_id"],))

    user = c.fetchone()
    conn.close()

    if not user:
        return "No users"

    return render_template_string(base_css + """
<div class="overlay">
<div class="glass">

{% if user[7] %}
<img src="{{user[7]}}">
{% endif %}

<h2>{{user[1]}}</h2>
<p>{{user[3]}}</p>

<a href="/like/{{user[0]}}"><button>❤️ Like</button></a>
<a href="/pass_user"><button style="background:#333">❌ Pass</button></a>

<br><br>
<a href="/profile">Back</a>

</div>
</div>
""", user=user)

# ---------------- LIKE ---------------- #

@app.route("/like/<int:user_id>")
def like(user_id):
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()

    c.execute("INSERT INTO likes(liker,liked) VALUES(?,?)",
              (session["user_id"], user_id))

    conn.commit()
    conn.close()

    return redirect("/swipe")

@app.route("/pass_user")
def pass_user():
    return redirect("/swipe")

# ---------------- MATCHES ---------------- #

@app.route("/matches")
def matches():
    conn = sqlite3.connect("dating.db")
    c = conn.cursor()

    c.execute("""
    SELECT u.username
    FROM users u
    JOIN likes l1 ON u.id=l1.liked
    JOIN likes l2 ON u.id=l2.liker
    WHERE l1.liker=? AND l2.liked=?
    """, (session["user_id"], session["user_id"]))

    results = c.fetchall()
    conn.close()

    html = base_css + """
<div class="overlay">
<div class="glass">
<h2>Matches ❤️</h2>
"""

    for r in results:
        html += f"<p>💘 {r[0]}</p>"

    html += "<br><a href='/profile'>Back</a></div></div>"
    return render_template_string(html)

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
