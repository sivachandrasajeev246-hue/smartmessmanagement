from flask import Blueprint, render_template, request, redirect, session
from models.user_model import get_user
from utils.decorators import role_required
import sqlite3
from datetime import datetime
from utils.ai_module import generate_insights
from ai.predictor import predict_attendance
from utils.ai_module import predict_attendance, predict_top_dish
auth_bp = Blueprint("auth", __name__)

# ---------------- LOGIN ----------------

@auth_bp.route("/", methods=["GET", "POST"])
def login():

    # 🔒 If already logged in → redirect
    if "user_id" in session:
        role = session.get("role")
        if role == "student":
            return redirect("/student")
        elif role == "manager":
            return redirect("/manager")
        elif role == "admin":
            return redirect("/admin")

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = get_user(email, password)

        if user:
            session["user_id"] = user[0]
            session["role"] = user[2]

            if user[2] == "student":
                return redirect("/student")
            elif user[2] == "manager":
                return redirect("/manager")
            elif user[2] == "admin":
                return redirect("/admin")
        else:
            return "Invalid credentials"

    return render_template("login.html")


# ---------------- DASHBOARDS ----------------

from flask import session, redirect

@auth_bp.route("/student")
def student_dashboard():

    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("auth.login"))

    user_id = session.get("user_id")
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 1️⃣ Meals taken today
    cursor.execute("""
        SELECT meal_type FROM attendance
        WHERE user_id = ? AND attendance_date = ?
    """, (user_id, today))

    meals_taken = [row[0] for row in cursor.fetchall()]

    # 2️⃣ Wallet balance
    cursor.execute("""
        SELECT balance FROM wallet
        WHERE user_id = ?
    """, (user_id,))

    wallet_data = cursor.fetchone()
    wallet_balance = wallet_data[0] if wallet_data else 0

    # 3️⃣ Rated meals
    cursor.execute("""
        SELECT DISTINCT dish.category
        FROM rating
        JOIN dish ON rating.dish_id = dish.dish_id
        JOIN menu ON dish.menu_id = menu.menu_id
        WHERE rating.user_id = ?
        AND menu.menu_date = ?
    """, (user_id, today))

    rated_meals = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "student_dashboard.html",
        meals_taken=len(meals_taken),
        wallet_balance=wallet_balance,
        rated_meals=rated_meals
    )

@auth_bp.route("/manager")
def manager_dashboard():

    if "user_id" not in session or session.get("role") != "manager":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    # 1️⃣ Today's attendance count
    cursor.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE attendance_date = ?
    """, (today,))
    todays_attendance = cursor.fetchone()[0]

    # 2️⃣ Today's menu dishes count
    cursor.execute("""
        SELECT COUNT(*) FROM dish
        JOIN menu ON dish.menu_id = menu.menu_id
        WHERE menu.menu_date = ?
    """, (today,))
    menu_updates = cursor.fetchone()[0]

    # 3️⃣ Today's feedback count
    cursor.execute("""
        SELECT COUNT(*) FROM rating
        JOIN dish ON rating.dish_id = dish.dish_id
        JOIN menu ON dish.menu_id = menu.menu_id
        WHERE menu.menu_date = ?
    """, (today,))
    pending_feedback = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "manager_dashboard.html",
        todays_attendance=todays_attendance,
        menu_updates=menu_updates,
        pending_feedback=pending_feedback
    )

@auth_bp.route("/manager/attendance", methods=["GET", "POST"])
def view_attendance():

    if "user_id" not in session or session.get("role") != "manager":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Default = today
    selected_date = datetime.now().date()

    if request.method == "POST":
        selected_date = request.form.get("attendance_date")

    # Meal-wise counts
    cursor.execute("""
        SELECT meal_type, COUNT(*) 
        FROM attendance
        WHERE attendance_date = ?
        GROUP BY meal_type
    """, (selected_date,))

    rows = cursor.fetchall()

    # Default values
    breakfast = 0
    lunch = 0
    dinner = 0

    for meal, count in rows:
        if meal == "breakfast":
            breakfast = count
        elif meal == "lunch":
            lunch = count
        elif meal == "dinner":
            dinner = count

    total = breakfast + lunch + dinner

    conn.close()

    return render_template(
        "manager_attendance.html",
        selected_date=selected_date,
        breakfast=breakfast,
        lunch=lunch,
        dinner=dinner,
        total=total
    )


@auth_bp.route("/admin")
def admin_dashboard():

    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Total users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Active managers
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='manager'")
    active_managers = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        active_managers=active_managers
    )





# ---------------- LOGOUT ----------------

from flask import session, redirect, url_for

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

# =====================================================
# ---------------- MODULE 2 : STUDENT -----------------
# =====================================================

import sqlite3
from datetime import datetime, time

# ---------------- ATTENDANCE SELECTION PAGE ----------------

@auth_bp.route("/student/attendance")
def attendance_page():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("auth.login"))
    return render_template("attendance_select.html")


# ---------------- QR DISPLAY PAGE ----------------

@auth_bp.route("/student/qr/<meal_type>")
def show_qr(meal_type):
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("auth.login"))

    valid_meals = ["breakfast", "lunch", "dinner"]
    if meal_type not in valid_meals:
        return "Invalid meal type"

    qr_file = meal_type + "_qr.png"
    return render_template("qr_page.html", meal=meal_type.capitalize(), qr_file=qr_file)


# ---------------- ATTENDANCE PROCESSING ----------------


@auth_bp.route("/student/attendance/process/<meal_type>")
def process_attendance(meal_type):

    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("auth.login"))

    user_id = session.get("user_id")

    valid_meals = ["breakfast", "lunch", "dinner"]
    if meal_type not in valid_meals:
        return render_template(
            "attendance_result.html",
            status="error",
            message="Invalid QR code."
        )

    # ---------------- TIME VALIDATION ----------------

    now = datetime.now().time()

    meal_times = {
        "breakfast": (time(8, 15), time(23, 40)),
        "lunch": (time(8, 15), time(23, 40)),
        "dinner": (time(8, 0), time(23, 40))
    }

    start, end = meal_times[meal_type]

    if not (start <= now <= end):
        return render_template(
            "attendance_result.html",
            status="error",
            message="Invalid meal time. Please scan within allowed time."
        )

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    # Check if already marked
    cursor.execute("""
        SELECT * FROM attendance
        WHERE user_id = ? AND meal_type = ? AND attendance_date = ?
    """, (user_id, meal_type, today))

    if cursor.fetchone():
        conn.close()
        return render_template(
            "attendance_result.html",
            status="error",
            message="Attendance already marked for this meal."
        )

    # Get wallet
    cursor.execute("SELECT wallet_id, balance FROM wallet WHERE user_id = ?", (user_id,))
    wallet = cursor.fetchone()

    if not wallet:
        conn.close()
        return render_template(
            "attendance_result.html",
            status="error",
            message="Wallet not found."
        )

    wallet_id, balance = wallet

    meal_costs = {
        "breakfast": 50,
        "lunch": 70,
        "dinner": 60
    }

    cost = meal_costs[meal_type]

    if balance < cost:
        conn.close()
        return render_template(
            "attendance_result.html",
            status="error",
            message="Insufficient wallet balance."
        )

    # Insert attendance
    cursor.execute("""
        INSERT INTO attendance (user_id, meal_type, attendance_date)
        VALUES (?, ?, ?)
    """, (user_id, meal_type, today))

    # Deduct wallet
    cursor.execute("""
        UPDATE wallet
        SET balance = balance - ?
        WHERE wallet_id = ?
    """, (cost, wallet_id))

    # Insert transaction
    cursor.execute("""
        INSERT INTO transactions (wallet_id, amount, transaction_type)
        VALUES (?, ?, ?)
    """, (wallet_id, -cost, "MEAL_" + meal_type.upper()))

    conn.commit()
    conn.close()

    return render_template(
        "attendance_result.html",
        status="success",
        message=f"{meal_type.capitalize()} attendance marked successfully!"
    )



#wallet

@auth_bp.route("/student/wallet")
def student_wallet():

    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("auth.login"))

    user_id = session.get("user_id")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT balance FROM wallet WHERE user_id = ?", (user_id,))
    wallet = cursor.fetchone()

    conn.close()

    if not wallet:
        return "Wallet not found"

    balance = wallet[0]

    return render_template("student_wallet.html", balance=balance)


#admin dash

@auth_bp.route("/admin/students")
def admin_view_students():

    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email
        FROM users
        WHERE role = 'student'
    """)

    students = cursor.fetchall()
    conn.close()

    return render_template("admin_students.html", students=students)


@auth_bp.route("/admin/student/<int:student_id>")
def admin_view_student_wallet(student_id):

    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get student details
    cursor.execute("""
        SELECT name, email FROM users
        WHERE id = ? AND role = 'student'
    """, (student_id,))

    student = cursor.fetchone()

    if not student:
        conn.close()
        return "Student not found"

    name, email = student

    # Get wallet
    cursor.execute("""
        SELECT wallet_id, balance
        FROM wallet
        WHERE user_id = ?
    """, (student_id,))

    wallet = cursor.fetchone()

    if not wallet:
        conn.close()
        return "Wallet not found"

    wallet_id, balance = wallet

    # Get transactions
    cursor.execute("""
        SELECT amount, transaction_type, timestamp
        FROM transactions
        WHERE wallet_id = ?
        ORDER BY timestamp DESC
    """, (wallet_id,))

    transactions = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_student_wallet.html",
        name=name,
        email=email,
        balance=balance,
        transactions=transactions
    )

@auth_bp.route("/admin/student/<int:student_id>/transactions")
def admin_student_transactions(student_id):

    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT wallet_id FROM wallet WHERE user_id = ?
    """, (student_id,))
    wallet = cursor.fetchone()

    if not wallet:
        conn.close()
        return "Wallet not found"

    wallet_id = wallet[0]

    cursor.execute("""
        SELECT amount, transaction_type, timestamp
        FROM transactions
        WHERE wallet_id = ?
        ORDER BY timestamp DESC
    """, (wallet_id,))

    transactions = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_transactions.html",
        transactions=transactions
    )
# =====================================================
# ---------------- MODULE 3 : STUDENT -----------------
# =====================================================

@auth_bp.route("/student/menu")
def student_view_menu():

    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    today = datetime.now().date()

    cursor.execute("SELECT menu_id FROM menu WHERE menu_date = ?", (today,))
    menu = cursor.fetchone()

    breakfast = []
    lunch = []
    dinner = []

    if menu:
        menu_id = menu[0]

        cursor.execute("""
            SELECT dish_id, name, category
            FROM dish
            WHERE menu_id = ?
        """, (menu_id,))

        dishes = cursor.fetchall()

        for dish in dishes:
            if dish[2] == "breakfast":
                breakfast.append(dish)
            elif dish[2] == "lunch":
                lunch.append(dish)
            elif dish[2] == "dinner":
                dinner.append(dish)

    conn.close()

    return render_template(
        "student_menu.html",
        breakfast=breakfast,
        lunch=lunch,
        dinner=dinner
    )
@auth_bp.route("/student/feedback", methods=["GET", "POST"])
def student_feedback():

    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("auth.login"))

    user_id = session.get("user_id")
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 1️⃣ Get meals attended today
    cursor.execute("""
        SELECT meal_type FROM attendance
        WHERE user_id = ? AND attendance_date = ?
    """, (user_id, today))

    meals_attended = [row[0] for row in cursor.fetchall()]

    if not meals_attended:
        conn.close()
        return render_template(
            "attendance_result.html",
            status="error",
            message="You must mark attendance before giving feedback."
        )

    # 2️⃣ Get today's menu
    cursor.execute("SELECT menu_id FROM menu WHERE menu_date = ?", (today,))
    menu = cursor.fetchone()

    if not menu:
        conn.close()
        return render_template(
            "attendance_result.html",
            status="error",
            message="No menu available for today."
        )

    menu_id = menu[0]

    # 3️⃣ Get dishes for attended meals
    cursor.execute("""
        SELECT dish_id, name, category
        FROM dish
        WHERE menu_id = ?
    """, (menu_id,))

    all_dishes = cursor.fetchall()

    # 4️⃣ Only show dishes NOT already rated
    dishes = []

    for d in all_dishes:
        if d[2] in meals_attended:

            cursor.execute("""
                SELECT 1 FROM rating
                WHERE user_id = ? AND dish_id = ?
            """, (user_id, d[0]))

            already_rated = cursor.fetchone()

            if not already_rated:
                dishes.append(d)

    # If nothing left to rate
    if not dishes:
        conn.close()
        return render_template(
            "feedback_result.html",
            status="success",
            message="Feedback already submitted for all attended meals."
        )

    # 5️⃣ Handle submission
    if request.method == "POST":

        for dish in dishes:
            rating_value = request.form.get(f"rating_{dish[0]}")
            if rating_value:
                cursor.execute("""
                    INSERT INTO rating
                    (user_id, dish_id, rating_value)
                    VALUES (?, ?, ?)
                """, (user_id, dish[0], int(rating_value)))

        conn.commit()
        conn.close()

        return render_template(
            "attendance_result.html",
            status="success",
            message="Feedback submitted successfully!"
        )

    conn.close()

    # 6️⃣ Group by category
    grouped = {
        "breakfast": [],
        "lunch": [],
        "dinner": []
    }

    for d in dishes:
        grouped[d[2]].append(d)

    return render_template("student_feedback.html", meals=grouped)
# =====================================================
# ---------------- MODULE 3 : MANAGER MENU ------------
# =====================================================

@auth_bp.route("/manager/menu", methods=["GET", "POST"])
def manager_menu():

    if "user_id" not in session or session.get("role") != "manager":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    # Ensure menu exists for today
    cursor.execute("SELECT menu_id FROM menu WHERE menu_date = ?", (today,))
    menu = cursor.fetchone()

    if not menu:
        cursor.execute("""
            INSERT INTO menu (menu_date, published_by)
            VALUES (?, ?)
        """, (today, session.get("user_id")))
        conn.commit()
        cursor.execute("SELECT menu_id FROM menu WHERE menu_date = ?", (today,))
        menu = cursor.fetchone()

    menu_id = menu[0]

    # Add dish
    if request.method == "POST":
        dish_name = request.form.get("dish_name")
        category = request.form.get("category")

        if dish_name and category:
            cursor.execute("""
                INSERT INTO dish (menu_id, name, category)
                VALUES (?, ?, ?)
            """, (menu_id, dish_name.strip(), category))
            conn.commit()

    # Fetch grouped dishes
    cursor.execute("""
        SELECT dish_id, name, category
        FROM dish
        WHERE menu_id = ?
    """, (menu_id,))

    rows = cursor.fetchall()

    breakfast = []
    lunch = []
    dinner = []

    for dish_id, name, category in rows:
        if category == "breakfast":
            breakfast.append((dish_id, name))
        elif category == "lunch":
            lunch.append((dish_id, name))
        elif category == "dinner":
            dinner.append((dish_id, name))

    conn.close()

    return render_template(
        "manager_menu.html",
        breakfast=breakfast,
        lunch=lunch,
        dinner=dinner
    )
@auth_bp.route("/manager/menu/delete/<int:dish_id>")
def delete_dish(dish_id):

    if "user_id" not in session or session.get("role") != "manager":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM dish WHERE dish_id = ?", (dish_id,))
    conn.commit()
    conn.close()

    return redirect("/manager/menu")
@auth_bp.route("/manager/feedback")
def manager_feedback():

    if "user_id" not in session or session.get("role") != "manager":
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT users.name, dish.name, rating.rating_value
        FROM rating
        JOIN users ON rating.user_id = users.id
        JOIN dish ON rating.dish_id = dish.dish_id
        JOIN menu ON dish.menu_id = menu.menu_id
        WHERE menu.menu_date = ?
    """, (today,))

    feedbacks = cursor.fetchall()
    conn.close()

    return render_template("manager_feedback.html", feedbacks=feedbacks)

@auth_bp.route("/student/meals")
def student_meals():

    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("auth.login"))

    user_id = session.get("user_id")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT meal_type, attendance_date
        FROM attendance
        WHERE user_id = ?
        ORDER BY attendance_date DESC
    """, (user_id,))

    meals = cursor.fetchall()
    conn.close()

    return render_template("student_meals.html", meals=meals)

@auth_bp.route("/manager/analytics")
def manager_analytics():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") not in ["admin", "manager"]:
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # =========================
    # Attendance Trend
    # =========================
    cursor.execute("""
        SELECT attendance_date, COUNT(*) 
        FROM attendance
        GROUP BY attendance_date
        ORDER BY attendance_date ASC
    """)
    attendance_rows = cursor.fetchall()

    attendance_data = [
        {"date": row[0], "count": row[1]}
        for row in attendance_rows
    ]

    # =========================
    # Dish Popularity
    # =========================
    cursor.execute("""
        SELECT dish.name,
               AVG(rating.rating_value),
               COUNT(rating.rating_id)
        FROM rating
        JOIN dish ON rating.dish_id = dish.dish_id
        GROUP BY dish.name
        ORDER BY AVG(rating.rating_value) DESC
    """)
    popularity_rows = cursor.fetchall()

    dish_popularity = [
        {
            "dish": row[0],
            "avg_rating": round(row[1], 2) if row[1] else 0,
            "total_reviews": row[2]
        }
        for row in popularity_rows
    ]

    # =========================
    # Revenue Trend
    # =========================
    cursor.execute("""
        SELECT DATE(timestamp), SUM(amount)
        FROM transactions
        WHERE transaction_type LIKE 'MEAL_%'
        GROUP BY DATE(timestamp)
        ORDER BY DATE(timestamp) ASC
    """)
    revenue_rows = cursor.fetchall()

    revenue_data = [
        {"date": row[0], "amount": abs(row[1])}
        for row in revenue_rows if row[1]
    ]

    # =========================
    # Summary Data
    # =========================
    cursor.execute("""
        SELECT SUM(amount)
        FROM transactions
        WHERE transaction_type LIKE 'MEAL_%'
    """)
    revenue_total = cursor.fetchone()[0]
    total_revenue = abs(revenue_total) if revenue_total else 0

    cursor.execute("SELECT COUNT(*) FROM rating")
    total_feedback = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "manager_analytics.html",
        attendance_data=attendance_data,
        dish_popularity=dish_popularity,
        revenue_data=revenue_data,
        total_revenue=total_revenue,
        total_feedback=total_feedback
    )
@auth_bp.route("/manager/export")
def manager_export():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") not in ["admin", "manager"]:
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # =========================
    # Fetch Data
    # =========================

    # Attendance
    cursor.execute("""
        SELECT attendance_date, COUNT(*) 
        FROM attendance
        GROUP BY attendance_date
        ORDER BY attendance_date DESC
    """)
    attendance_data = cursor.fetchall()

    # Dish Popularity
    cursor.execute("""
        SELECT dish.name,
               AVG(rating.rating_value),
               COUNT(rating.rating_id)
        FROM rating
        JOIN dish ON rating.dish_id = dish.dish_id
        GROUP BY dish.name
        ORDER BY AVG(rating.rating_value) DESC
    """)
    popularity_data = cursor.fetchall()

    # Revenue
    cursor.execute("""
        SELECT SUM(amount)
        FROM transactions
        WHERE transaction_type LIKE 'MEAL_%'
    """)
    revenue_row = cursor.fetchone()
    total_revenue = abs(revenue_row[0]) if revenue_row and revenue_row[0] else 0

    # Feedback count
    cursor.execute("SELECT COUNT(*) FROM rating")
    total_feedback = cursor.fetchone()[0]

    conn.close()

    # =========================
    # Generate CSV
    # =========================

    import csv
    from io import StringIO
    from flask import Response

    output = StringIO()
    writer = csv.writer(output)

    # HEADER
    writer.writerow(["SMART MESS MANAGEMENT SYSTEM"])
    writer.writerow(["Analytics Report"])
    writer.writerow([])

    # SUMMARY
    writer.writerow(["SUMMARY"])
    writer.writerow(["Total Revenue (₹)", total_revenue])
    writer.writerow(["Total Feedback", total_feedback])
    writer.writerow([])

    # ATTENDANCE
    writer.writerow(["ATTENDANCE TREND"])
    writer.writerow(["Date", "Total Attendance"])

    for date, count in attendance_data:
        # Force Excel to treat date as text
        safe_date = f"'{date}"
        writer.writerow([safe_date, count])

    writer.writerow([])

    # DISH POPULARITY
    writer.writerow(["DISH POPULARITY"])
    writer.writerow(["Dish Name", "Average Rating", "Total Reviews"])

    for name, avg_rating, reviews in popularity_data:
        avg = round(avg_rating, 2) if avg_rating else 0
        writer.writerow([name, avg, reviews])

    # Create Response
    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=analytics_report.csv"
        }
    )

    return response


from ai.predictor import predict_attendance
from ai.food_predictor import predict_top_dish
from datetime import datetime


@auth_bp.route("/manager/ai-insight")
def manager_ai_insight():

    if "user_id" not in session or session.get("role") != "manager":
        return redirect(url_for("auth.login"))

    (
        attendance_data,
        attendance_summary,
        top_meal,
        top_dish,
        top_rating,
        total_days,
        growth_rate,
        volatility_score,
        dish_risk_score
    ) = generate_insights()

    # ----------------------------------
    # Since attendance_data already holds
    # PER-DAY AVERAGES → do NOT divide again
    # ----------------------------------
    total_students = round(sum(attendance_data.values()), 2)
    average_per_day = total_students

    # Participation Spread
    if attendance_data:
        max_count = max(attendance_data.values())
        min_count = min(attendance_data.values())
        participation_spread = round(max_count - min_count, 2)
    else:
        participation_spread = 0

    # Stability Index
    if total_students > 0:
        stability_index = round(1 - (participation_spread / total_students), 2)
    else:
        stability_index = 0

    # Satisfaction Score
    if top_rating:
        satisfaction_score = round(top_rating / 5, 2)
    else:
        satisfaction_score = 0

    # Confidence based on historical days
    if total_days <= 2:
        confidence = "LOW"
    elif total_days <= 5:
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"

    # Rating Reliability
    if top_rating:
        if top_rating < 3:
            reliability = "LOW"
        elif top_rating < 4:
            reliability = "MEDIUM"
        else:
            reliability = "HIGH"
    else:
        reliability = "LOW"

    # Executive Summary
    summary = [
    f"Highest participation meal: {top_meal.capitalize() if top_meal else 'N/A'}.",
    f"Top rated dish: {top_dish if top_dish else 'N/A'} (Avg Rating: {top_rating}).",
    f"Average daily meal participation: {average_per_day}.",
    f"Participation growth trend: {growth_rate}%.",
    "Meal participation computed using per-day aggregation.",
    "Dish ranking derived via mean rating normalization.",
    "Fully explainable rule-based analytics (no ML black-box)."
]
    average_per_day=total_students
    # Explainability Block
    explainability = [
        f"Analyzed {total_days} distinct attendance days.",
        "Participation percentage derived from relative frequency.",
        "Top meal selected via maximum average comparison.",
        f"Growth rate calculated between first and last recorded day.",
        f"Volatility score computed using standard deviation of daily totals.",
        f"Dish risk score normalized from lowest rating.",
        "Confidence derived from historical volume.",
        "Stability Index measures distribution uniformity."
    ]

    breakfast_count = attendance_data.get("breakfast", 0)
    lunch_count = attendance_data.get("lunch", 0)
    dinner_count = attendance_data.get("dinner", 0)

    return render_template(
        "manager_ai_insight.html",
        attendance_data=attendance_data,
        attendance_summary=attendance_summary,
        top_meal=top_meal,
        top_dish=top_dish,
        top_rating=top_rating,
        confidence=confidence,
        summary=summary,
        reliability=reliability,
        breakfast_count=breakfast_count,
        lunch_count=lunch_count,
        dinner_count=dinner_count,
        total_students=total_students,
        average_per_day=average_per_day,
        participation_spread=participation_spread,
        total_days=total_days,
        stability_index=stability_index,
        satisfaction_score=satisfaction_score,
        growth_rate=growth_rate,
        volatility_score=volatility_score,
        dish_risk_score=dish_risk_score,
        explainability=explainability
    )