from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, random, time
from functools import wraps
import os
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-key")
DB = "quiz.db"

QUESTIONS = [
    ("Which keyword is used to define a function in Python?", ["func", "define", "def", "function"], "def"),
    ("Which data type stores True or False?", ["int", "bool", "str", "float"], "bool"),
    ("What is the output of print(2 ** 3)?", ["6", "8", "9", "5"], "8"),
    ("Which symbol is used for comments in Python?", ["//", "/*", "#", "--"], "#"),
    ("Which collection is ordered and changeable?", ["tuple", "set", "list", "frozenset"], "list"),
    ("What does len('Python') return?", ["5", "6", "7", "Python"], "6"),
    ("Which method adds an item to the end of a list?", ["add()", "append()", "insertEnd()", "push()"], "append()"),
    ("Which loop is commonly used to iterate over a sequence?", ["repeat", "foreach", "for", "loop"], "for"),
    ("What is the correct extension for a Python file?", [".pt", ".py", ".python", ".pyt"], ".py"),
    ("Which statement handles exceptions?", ["catch", "error", "try-except", "handle"], "try-except"),
    ("What is the output of print(10 // 3)?", ["3.33", "3", "4", "1"], "3"),
    ("Which function converts a value to an integer?", ["int()", "integer()", "str()", "float()"], "int()"),
    ("A dictionary stores data as:", ["indexes only", "key-value pairs", "single values", "characters"], "key-value pairs"),
    ("Which keyword exits a loop immediately?", ["stop", "exit", "break", "return"], "break"),
    ("Which operator checks equality?", ["=", "==", "!=", "==="], "=="),
    ("What is the result of bool(0)?", ["True", "False", "0", "None"], "False"),
    ("Which function displays output?", ["input()", "show()", "print()", "display()"], "print()"),
    ("Which keyword is used to import a module?", ["include", "using", "import", "module"], "import"),
    ("What is a tuple usually written with?", ["[]", "{}", "()", "<>"], "()"),
    ("Which value represents no value in Python?", ["null", "nil", "None", "void"], "None"),
]

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS attempts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_index INTEGER NOT NULL,
            selected TEXT,
            correct INTEGER NOT NULL,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        con.execute("""CREATE TABLE IF NOT EXISTS scores(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

init_db()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(password) < 4:
            flash("Username must be 3+ characters and password 4+ characters.")
            return render_template("register.html")
        try:
            with connect() as con:
                con.execute("INSERT INTO users(username,password) VALUES(?,?)",
                            (username, generate_password_hash(password)))
            flash("Account created! Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists. Choose another.")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with connect() as con:
            user = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Incorrect username or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    with connect() as con:
        scores = con.execute("SELECT * FROM scores WHERE user_id=? ORDER BY id DESC LIMIT 5",
                             (session["user_id"],)).fetchall()
        total = con.execute("SELECT COUNT(*) FROM scores WHERE user_id=?",
                            (session["user_id"],)).fetchone()[0]
    return render_template("dashboard.html", scores=scores, total_attempts=total)

@app.route("/quiz/start")
@login_required
def quiz_start():
    # Pick 10 questions not answered correctly before; reset pool after all have been completed.
    uid = session["user_id"]
    with connect() as con:
        done = {r["question_index"] for r in con.execute(
            "SELECT DISTINCT question_index FROM attempts WHERE user_id=? AND correct=1", (uid,))}
     
    available = [i for i in range(len(QUESTIONS)) if i not in done]

    if not available:
        with connect() as con:
            con.execute("DELETE FROM attempts WHERE user_id=?", (uid,))
        available = list(range(len(QUESTIONS)))
        flash("Great! You completed the question bank. Your practice cycle has been reset.")

    chosen = random.sample(available, min(10, len(available)))
    session["quiz_questions"] = chosen
    session["quiz_answers"] = {}
    session["quiz_started"] = time.time()
    return redirect(url_for("quiz_question", number=0))

@app.route("/quiz/<int:number>", methods=["GET", "POST"])
@login_required
def quiz_question(number):
    chosen = session.get("quiz_questions", [])
    if not chosen:
        return redirect(url_for("quiz_start"))
    if number < 0 or number >= len(chosen):
        return redirect(url_for("quiz_question", number=0))
    if request.method == "POST":
        session["quiz_answers"][str(number)] = request.form.get("answer", "")
        session.modified = True
        if number + 1 < len(chosen):
            return redirect(url_for("quiz_question", number=number+1))
        return redirect(url_for("quiz_result"))
    qi = chosen[number]
    q = QUESTIONS[qi]
    return render_template("question.html", number=number, total=len(chosen),
                           question=q[0], options=q[1], selected=session.get("quiz_answers", {}).get(str(number)))

@app.route("/quiz/result")
@login_required
def quiz_result():
    chosen = session.get("quiz_questions", [])
    answers = session.get("quiz_answers", {})
    if not chosen:
        return redirect(url_for("dashboard"))
    score = 0
    uid = session["user_id"]
    with connect() as con:
        for pos, qi in enumerate(chosen):
            selected = answers.get(str(pos), "")
            correct_answer = QUESTIONS[qi][2]
            correct = int(selected == correct_answer)
            score += correct
            con.execute("INSERT INTO attempts(user_id,question_index,selected,correct) VALUES(?,?,?,?)",
                        (uid, qi, selected, correct))
        con.execute("INSERT INTO scores(user_id,score,total) VALUES(?,?,?)", (uid, score, len(chosen)))
    session.pop("quiz_questions", None)
    session.pop("quiz_answers", None)
    return render_template("result.html", score=score, total=len(chosen),
                           percentage=round(score/len(chosen)*100))

if __name__ == "__main__":
    app.run(debug=False)
