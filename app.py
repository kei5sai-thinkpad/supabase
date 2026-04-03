import os
import re
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# --- 設定 ---
app = Flask(__name__)

# 🔥 Supabase接続（環境変数から取得）
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")

# Render対策（postgres → postgresql）
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace(
        "postgres://", "postgresql://", 1
    )

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 🔥 環境変数で秘密鍵
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev_secret")

db = SQLAlchemy(app)

# --- モデル ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), default='名無し')
    content = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)

    replies = db.relationship('Reply', backref='post', cascade="all, delete-orphan")

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    username = db.Column(db.String(30), default='名無し')
    content = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)

# --- ヘルパー ---
def auto_link(text):
    return re.sub(r'(https?://[^\s]+)', r'<a href="\1" target="_blank">\1</a>', text)

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper

# --- 初期データ ---
def init_db():
    db.create_all()
    if not Post.query.first():
        p = Post(
            username="👑管理人",
            content="ようこそ！",
            password_hash=generate_password_hash("adminpass"),
            is_admin=True
        )
        db.session.add(p)
        db.session.commit()

# --- ルート ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username") or "名無し"
        content = request.form["content"]
        password = request.form["password"]

        post = Post(
            username=username,
            content=content,
            password_hash=generate_password_hash(password),
            is_admin=session.get("admin", False)
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("index"))

    posts = Post.query.filter_by(is_deleted=False).order_by(Post.created_at.desc()).all()
    for p in posts:
        p.content = auto_link(p.content)

    return render_template("index.html", posts=posts)

@app.route("/reply/<int:post_id>", methods=["POST"])
def reply(post_id):
    content = request.form["content"]
    password = request.form["password"]

    r = Reply(
        post_id=post_id,
        content=content,
        password_hash=generate_password_hash(password)
    )
    db.session.add(r)
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    post = Post.query.get_or_404(id)
    password = request.form["password"]

    if check_password_hash(post.password_hash, password) or session.get("admin"):
        post.is_deleted = True
        db.session.commit()

    return redirect(url_for("index"))

@app.route("/login", methods=["POST"])
def login():
    if request.form["password"] == "adminpass":
        session["admin"] = True
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

# --- 起動 ---
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
