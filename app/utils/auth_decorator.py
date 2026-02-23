import jwt
from flask import request, redirect
from functools import wraps
import os

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("token")

        if not token:
            return redirect("/login-form")

        try:
            decoded = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
            request.user_id = decoded["user_id"]
            request.role = decoded["role"]
        except:
            return redirect("/login-form")

        return f(*args, **kwargs)

    return decorated