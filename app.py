import sqlite3
from flask import Flask, flash, redirect, render_template, request, url_for, jsonify
from flask_login import LoginManager, current_user, login_required, login_user
from db import DB
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "123"
login_manager = LoginManager(app)

class UserLogin:
    def fromDB(self, username):
        db = DB("database.db")
        self.user = db.get_user_by_username(username)
        db.close()
        return self
            
    def fromDBid(self, user_id):
        db = DB("database.db")
        self.user = db.get_user_by_id(user_id)
        db.close()
        return self
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.user[0])
    
@login_manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDBid(user_id)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not (username and password):
            flash("Введіть логін та пароль!!!")
        else:
            db = DB("database.db")
            user = db.get_user_by_username(username)
            db.close()
            if user:
                user_password = user[2]
                if check_password_hash(pwhash=user_password, password=password):
                    login_user(UserLogin().fromDB(username))
                    return redirect(url_for("notes"))
            flash("Неправильний логін або пароль")
    return render_template("login.html")
   
@app.route("/register_tg", methods=["POST"])
def register_tg():
    username = request.form.get("username")
    password = request.form.get("password")
    telegram_id = request.form.get("telegram_id")
    if not (username and password and telegram_id):
        return jsonify({"error": "Введіть логін та пароль правильно!!!"})
    
    db = DB("database.db")
    pwhash = generate_password_hash(password)
    try:
        db.add_user(username=username, password=pwhash, telegram_id=telegram_id)
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Ім'я вже зайнято"})
    else:
        return jsonify({"message": "Користувач створений"})    
    finally:
        db.close()        
        
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        password_rep = request.form.get("password-rep")
        if not (username and password and (password == password_rep)):
            flash("Введіть логін та пароль правильно!!!")
        else:
            db = DB("database.db")
            pwhash = generate_password_hash(password)
            try:
                db.add_user(username=username, password=pwhash)
                db.commit()
            except sqlite3.IntegrityError:
                flash(f"Ім'я {username} вже зайнято, оберіть інше")
            else:
                return redirect(url_for("login"))
            finally:
                db.close()
    return render_template("register.html")


@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    db = DB("database.db")
    user_id = current_user.get_id()
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        priority = request.form.get("priority")
        deadline = request.form.get("deadline")
        deadline = deadline.replace("T", " ")
        created_at = datetime.now().strftime("%Y-%m-%dT%H:%M")
        created_at = created_at.replace("T", " ")
        db.add_note(title=title, content=content, priority=priority, 
                    deadline_date=deadline, author_id=user_id, created_at=created_at)
        db.commit()
    notes = db.get_user_notes(user_id)
    db.close()
    return render_template("notes.html", notes=notes)


@app.route("/del_note", methods=["POST"])
def del_note():
    note_id = request.form.get("note_id")
    db = DB("database.db")
    db.delete_note(note_id)
    db.commit()
    db.close()
    return redirect(url_for("notes"))

@app.route("/link_tg", methods=["POST"])
def link_tg():
    username = request.form.get("username", None)
    password = request.form.get("password", None)
    telegram_id = request.form.get("telegram_id", None)
    if username and password and telegram_id:
        db = DB()
        user = db.get_user_by_username(username)
        if user:
            pw_hash = user[2]
            if check_password_hash(pw_hash, password):
                db.link_tg(user[0], telegram_id)
                db.commit()
                db.close()
                return jsonify({"message": "Successfully linled"})
        db.close()
        return jsonify({"error": "Not valid username or password"})
    return jsonify({"error2": "Not provided username or password or telegram_id"})
    
@app.route("/notes_list")
def show_notes():
    telegram_id = request.args.get("telegram_id")
    db = DB()
    user = db.get_user_by_telegram(telegram_id)
    user_id = user[0]
    notes = db.get_user_notes(user_id)
    db.close()
    return jsonify({"notes": notes})
    
@app.route("/check_tg")
def check_tg():
    telegram_id = request.args.get("telegram_id")
    db = DB()
    user = db.get_user_by_telegram(telegram_id)
    db.close()
    if user:
        return jsonify({"status": True})
    return jsonify({"status": False})

@app.route("/unlink")
def unlink():
    telegram_id = request.args.get("telegram_id")
    db = DB()
    db.unlink(telegram_id)
    db.commit()
    db.close()
    return jsonify({"status": "OK"})

@app.route("/add_task", methods=["POST"])
def add_task():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        priority = request.form.get("priority")
        deadline = request.form.get("deadline")
        telegram_id = request.form.get("telegram_id")
        if not title or not content or not priority or not deadline or not telegram_id:
            return jsonify({"error": "Перевір як ти вводив данні."})
            
        try:
            db = DB("database.db")
            user = db.get_user_by_telegram(telegram_id)[0]
            db.add_note(title=title, content=content, priority=priority, 
                        deadline_date=deadline, author_id=user, created_at=datetime.now().strftime("%Y-%m-%d %H:%M"))
            db.commit()
            db.close()
            return jsonify({"status": "Таск додано!"})
        except Exception as e:
            return jsonify({"error": e.args[0]})
        
    
app.run(debug=True)
