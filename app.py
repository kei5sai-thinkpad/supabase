import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

# --- Flask ---
app = Flask(__name__)

# --- DB設定 ---
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///board.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "secret"

# 🔥 ここが最重要（順番）
db = SQLAlchemy(app)

# --- モデル ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), default="名無し")
    content = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

# 🔥 ここも最重要（モデルの後）
with app.app_context():
    db.create_all()

# --- URLリンク化 ---
def auto_link(text):
    return re.sub(r"(https?://[^\s]+)", r'<a href="\1" target="_blank">\1</a>', text)

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

    posts = Post.query.order_by(Post.created_at.desc()).all()

    for p in posts:
        p.linked_content = auto_link(p.content)

    return render_template("index.html", posts=posts)

# --- 起動 ---
if __name__ == "__main__":
    app.run(debug=True)
