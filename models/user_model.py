import sqlite3
from werkzeug.security import check_password_hash

def get_user(email, password):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, password, role FROM users WHERE email=?",
        (email,)
    )

    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[2], password):
        return (user[0], user[1], user[3])

    return None

