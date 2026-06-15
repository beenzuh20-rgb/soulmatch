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
    font-family:'Segoe UI',sans-serif;
    background:url('https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?auto=format&fit=crop&w=1600&q=80');
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
    width:450px;
    background:rgba(255,255,255,0.12);
    backdrop-filter:blur(20px);
    -webkit-backdrop-filter:blur(20px);
    border:1px solid rgba(255,255,255,0.2);
    border-radius:25px;
    padding:30px;
    color:white;
    box-shadow:
        0 8px 32px rgba(0,0,0,0.35),
        inset 0 1px 1px rgba(255,255,255,0.2);
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
    padding:14px;
    border:none;
    border-radius:50px;
    background:linear-gradient(135deg,#ff416c,#ff4b2b);
    color:white;
    font-weight:bold;
    font-size:16px;
    cursor:pointer;
    transition:all .3s ease;
}

.match-card{
    background:rgba(255,255,255,.12);
    padding:15px;
    border-radius:20px;
    margin:15px 0;
}

button:hover{
    transform:translateY(-2px);
    box-shadow:0 8px 20px rgba(255,75,110,.4);
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

       c.execute("SELECT * FROM users WHERE username=?",
          (request.form["username"],))
user = c.fetchone()

if user and check_password_hash(user[2], request.form["password"]):
    session["user_id"] = user[0]
    return redirect("/profile")
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/profile")

        return "Invalid login"

    return render_template_string(base_css + """
<div class="overlay">
<div class="glass">
<h1 style="text-align:center;font-size:42px;color:white;margin-bottom:0;">
💘 SoulMatch
</h1>

<p style="text-align:center;color:#ddd;margin-top:5px;">
Find Love. Build Connections.
</p>
<h2>Login</h2>
<form method="post">
<input name="username">
<input name="password" type="password">
<button>Login</button>
</form>
<p style="text-align:center; margin-top:10px;">
    Don't have an account?
    <a href="/signup">Sign up</a>
</p>
</div>
</div>
""")

# ---------------- SIGNUP ---------------- #

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        conn = sqlite3.connect("dating.db")
        c = conn.cursor()

hashed_pw = generate_password_hash(request.form["password"])

c.execute(
    "INSERT INTO users(username, password) VALUES(?,?)",
    (request.form["username"], hashed_pw)
)

        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template_string(base_css + """
<div class="overlay">
<div class="glass">
<h1 style="text-align:center;font-size:42px;color:white;margin-bottom:0;">
💘 SoulMatch
</h1>

<p style="text-align:center;color:#ddd;margin-top:5px;">
Find Love. Build Connections.
</p>
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

    return render_template("profile.html", user=user)
<div class="overlay">
<div class="glass">
<h1 style="text-align:center;font-size:42px;color:white;margin-bottom:0;">
💘 SoulMatch
</h1>

<p style="text-align:center;color:#ddd;margin-top:5px;">
Find Love. Build Connections.
</p>
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

    c.execute("""
    SELECT *
    FROM users
    WHERE id != ?
    AND id NOT IN(
        SELECT liked
        FROM likes
        WHERE liker=?
    )
    ORDER BY RANDOM()
    LIMIT 1
    """, (
        session["user_id"],
        session["user_id"]
    ))

    user = c.fetchone()
    conn.close()

    if not user:
        return "No users"

    return render_template_string(base_css + """
<div class="overlay">
<div class="glass">

<h1 style="text-align:center;font-size:42px;color:white;margin-bottom:0;">
💘 SoulMatch
</h1>

<p style="text-align:center;color:#ddd;margin-top:5px;">
Find Love. Build Connections.
</p>
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

    me = session["user_id"]

    c.execute(
        "INSERT INTO likes(liker,liked) VALUES(?,?)",
        (me,user_id)
    )

    c.execute("""
    SELECT *
    FROM likes
    WHERE liker=? AND liked=?
    """,(user_id,me))

    mutual = c.fetchone()

    conn.commit()
    conn.close()

    if mutual:
        return """
        <h1>🎉 It's a Match!</h1>
        <a href='/matches'>View Matches</a>
        """

    return redirect("/swipe")
# ---------------- MATCHES ---------------- #

@app.route("/matches")
def matches():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("dating.db")
    c = conn.cursor()

    c.execute("""
    SELECT u.*
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

    for user in results:

        photo = user[7] if user[7] else ""

        html += f"""
        <div class='match-card'>

            <img src='{photo}'>

            <h3>{user[1]}</h3>

            <p>{user[6]}</p>

            <a href='/chat/{user[0]}'>
                <button>💬 Message</button>
            </a>

        </div>
        """

    html += """
    <br>
    <a href='/profile'>Back</a>
    </div>
    </div>
    """

    return render_template_string(html)
# ---------------- RUN ---------------- #
@app.route("/chat/<int:user_id>", methods=["GET","POST"])
def chat(user_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("dating.db")
    c = conn.cursor()

    me = session["user_id"]

    if request.method == "POST":

        c.execute("""
        INSERT INTO messages(sender,receiver,message)
        VALUES(?,?,?)
        """, (
            me,
            user_id,
            request.form["message"]
        ))

        conn.commit()

    c.execute("""
    SELECT *
    FROM messages
    WHERE
    (sender=? AND receiver=?)
    OR
    (sender=? AND receiver=?)
    ORDER BY id
    """, (
        me,user_id,
        user_id,me
    ))

    messages = c.fetchall()

    c.execute(
        "SELECT username FROM users WHERE id=?",
        (user_id,)
    )

    other_user = c.fetchone()

    conn.close()

    html = base_css + f"""
    <div class='overlay'>
    <div class='glass'>

    <h2>Chat with {other_user[0]}</h2>
    """

    for msg in messages:

        sender = "You" if msg[1] == me else other_user[0]

        html += f"""
        <p>
        <b>{sender}:</b>
        {msg[3]}
        </p>
        """

    html += f"""
    <form method='post'>

    <input
        name='message'
        placeholder='Type message...'>

    <button>Send</button>

    </form>

    <br>

    <a href='/matches'>Back</a>

    </div>
    </div>
    """

    return render_template_string(html)
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
