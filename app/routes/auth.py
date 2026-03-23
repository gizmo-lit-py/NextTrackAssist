from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import SessionLocal
from app.models.user import User


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
        except IntegrityError:
            db.rollback()
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
            return redirect(url_for("tracks.index"))

        flash("メールアドレスまたはパスワードが違います。", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))