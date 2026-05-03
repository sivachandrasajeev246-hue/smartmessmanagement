from functools import wraps
from flask import session, redirect

def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                return redirect("/")
            return func(*args, **kwargs)
        return wrapper
    return decorator
