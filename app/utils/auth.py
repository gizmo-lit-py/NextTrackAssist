from functools import wraps
from flask import session, redirect


def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")

        return func(*args, **kwargs)

    return wrapper