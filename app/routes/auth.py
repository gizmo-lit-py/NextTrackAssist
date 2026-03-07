from flask import Blueprint, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import SessionLocal
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        db = SessionLocal()

        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        user = User(
            email=email,
            password=hashed_password
        )

        db.add(user)
        db.commit()

        db.close()

        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        db = SessionLocal()

        email = request.form["email"]
        password = request.form["password"]

        user = db.query(User).filter(User.email == email).first()

        db.close()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id

            return redirect(url_for("tracks.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("auth.login"))