import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db = SessionLocal()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if len(password) < 8:
            db.close()
            flash("パスワードは8文字以上にしてください。", "error")
            return render_template("auth/register.html")

        hashed_password = generate_password_hash(password)
        user = User(email=email, password_hash=hashed_password)

        try:
            db.add(user)
            db.commit()
            logger.info("ユーザー登録: email=%s", email)
        except IntegrityError:
            db.rollback()
            logger.warning("ユーザー登録失敗（重複）: email=%s", email)
            flash("このメールアドレスはすでに登録済みです。", "error")
            return render_template("auth/register.html")
        finally:
            db.close()

        flash("登録しました。ログインしてください。", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = SessionLocal()

        try:
            email = request.form["email"].strip().lower()
            password = request.form["password"]
            user = db.query(User).filter(User.email == email).first()
        finally:
            db.close()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            logger.info("ログイン成功: user=%s", user.id)
            return redirect(url_for("tracks.index"))
        
        logger.warning("ログイン失敗: email=%s", email)
        flash("メールアドレスまたはパスワードが違います。", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """POST のみ受け付ける（CSRF 対策: GET でのログアウトを防止）。"""
    user_id = session.get("user_id")
    session.clear()
    logger.info("ログアウト: user=%s", user_id)
    return redirect(url_for("auth.login"))