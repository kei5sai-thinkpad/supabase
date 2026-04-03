import os
import re
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- 設定 ---
app = Flask(__name__)

# 🔥 Supabase対応（環境変数優先）
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # postgres:// → postgresql:// に変換（重要）
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///board.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "secret-key")

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

db = SQLAlchemy(app)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- モデル ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), default="名無し")
    content = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_admin = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    image_filename = db.Column(db.String(255))
    replies = db.relationship("Reply", backref="post", lazy=True, cascade="all, delete-orphan")

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    username = db.Column(db.String(30), default="名無し")
    content = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_admin = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)

# --- 初期化（ここ重要🔥）---
with app.app_context():
    db.create_all()

# --- ヘルパー ---
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def auto_link_content(text):
    return re.sub(r"(https?://[^\s]+)", r'<a href="\1" target="_blank">\1</a>', text)

def process_posts(posts):
    for post in posts:
        post.replies_list = Reply.query.filter_by(post_id=post.id).all()
        post.linked_content = auto_link_content(post.content)
        for r in post.replies_list:
            r.linked_content = auto_link_content(r.content)
    return posts

# --- ルート ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        content = request.form["content"]
        password = request.form["password"]
        username = request.form.get("username") or "名無し"

        post = Post(
            username=username,
            content=content,
            password_hash=generate_password_hash(password)
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("index"))

    posts = Post.query.filter_by(is_deleted=False).order_by(Post.created_at.desc()).all()
    posts = process_posts(posts)
    return render_template("index.html", posts=posts)

# --- 起動 ---
if __name__ == "__main__":
    app.run(debug=True)
