from functools import wraps

from flask import g, redirect, session, url_for

from app.extensions import SessionLocal
from app.models.user import User


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            return redirect(url_for("auth.login"))

        db = SessionLocal()
        try:
            user = db.get(User, user_id)
        finally:
            db.close()

        if user is None:
            session.clear()
            return redirect(url_for("auth.login"))

        g.current_user = user
        return func(*args, **kwargs)

    return wrapper