import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# ---------------- USERS TABLE ----------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# ---------------- WALLET TABLE ----------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS wallet (
    wallet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    balance REAL NOT NULL CHECK(balance >= 0),
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

# ---------------- ATTENDANCE TABLE ----------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    meal_type TEXT NOT NULL,
    attendance_date DATE NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, meal_type, attendance_date)
)
""")

# ---------------- TRANSACTIONS TABLE ----------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    transaction_type TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_id) REFERENCES wallet(wallet_id)
)
""")

# ---------------- MENU TABLE ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS menu (
    menu_id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_date DATE NOT NULL UNIQUE,
    published_by INTEGER,
    FOREIGN KEY (published_by) REFERENCES users(id)
)
""")
# ---------------- DISH TABLE ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS dish (
    dish_id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('breakfast','lunch','dinner')),
    FOREIGN KEY (menu_id) REFERENCES menu(menu_id)
)
""")
# ---------------- RATING TABLE ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS rating (
    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    dish_id INTEGER NOT NULL,
    rating_value INTEGER CHECK(rating_value BETWEEN 1 AND 5),
    comment TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (dish_id) REFERENCES dish(dish_id),
    UNIQUE(user_id, dish_id)
)
""")
# ---------------- CLEAR USERS (for fresh start) ----------------

cursor.execute("DELETE FROM users")

student_pw = generate_password_hash("123")
manager_pw = generate_password_hash("123")
admin_pw = generate_password_hash("123")

cursor.execute(
    "INSERT INTO users VALUES (NULL,?,?,?,?)",
    ("Student One", "student1@test.com", student_pw, "student")
)

cursor.execute(
    "INSERT INTO users VALUES (NULL,?,?,?,?)",
    ("Student Two", "student2@test.com", student_pw, "student")
)

cursor.execute(
    "INSERT INTO users VALUES (NULL,?,?,?,?)",
    ("Student Three", "student3@test.com", student_pw, "student")
)

cursor.execute(
    "INSERT INTO users VALUES (NULL,?,?,?,?)",
    ("Manager One", "manager@test.com", manager_pw, "manager")
)

cursor.execute(
    "INSERT INTO users VALUES (NULL,?,?,?,?)",
    ("Admin", "admin@test.com", admin_pw, "admin")
)

# ---------------- CREATE WALLET FOR STUDENT ----------------

cursor.execute("SELECT id FROM users WHERE role='student'")
students = cursor.fetchall()

for (user_id,) in students:
    cursor.execute("""
        INSERT OR IGNORE INTO wallet (user_id, balance)
        VALUES (?, ?)
    """, (user_id, 60000.0))

conn.commit()
conn.close()

print("Database initialized with full Module 1 + Module 2 schema!")

