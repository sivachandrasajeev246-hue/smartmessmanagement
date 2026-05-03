import sqlite3
from datetime import datetime


# -----------------------------
# ATTENDANCE PREDICTION
# -----------------------------
def predict_attendance():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT attendance_date, meal_type, COUNT(*)
        FROM attendance
        GROUP BY attendance_date, meal_type
        ORDER BY attendance_date
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None, ["No historical attendance data available."]

    data = {}
    for date, meal, count in rows:
        data.setdefault(meal, []).append(count)

    predictions = {}
    explanations = []

    for meal, counts in data.items():
        avg = sum(counts) / len(counts)
        predictions[meal] = round(avg)

        # Confidence logic
        if len(counts) <= 2:
            confidence = "Low"
        elif len(counts) <= 5:
            confidence = "Medium"
        else:
            confidence = "High"

        # Trend detection
        trend = "Stable"
        if len(counts) >= 2:
            if counts[-1] > counts[-2]:
                trend = "Increasing"
            elif counts[-1] < counts[-2]:
                trend = "Decreasing"

        explanations.append(
            f"{meal.capitalize()}: Based on {len(counts)} days data. "
            f"Trend: {trend}. Confidence: {confidence}."
        )

    return predictions, explanations


# -----------------------------
# DISH PREDICTION
# -----------------------------
def predict_top_dish():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT dish.name,
               AVG(rating.rating_value),
               COUNT(rating.rating_id)
        FROM rating
        JOIN dish ON rating.dish_id = dish.dish_id
        GROUP BY dish.name
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None, None, ["No rating data available."]

    best_dish = None
    best_rating = 0

    worst_dish = None
    worst_rating = 5

    explanations = []

    for name, avg, count in rows:

        if count >= 2:  # vote threshold

            if avg > best_rating:
                best_rating = avg
                best_dish = name

            if avg < worst_rating:
                worst_rating = avg
                worst_dish = name

    if not best_dish:
        return None, None, ["Not enough rating votes for reliable prediction."]

    explanations.append(
        f"Top dish: {best_dish} (Avg: {round(best_rating,2)}). "
        "Minimum vote threshold applied."
    )

    explanations.append(
        f"Least preferred dish: {worst_dish} (Avg: {round(worst_rating,2)})."
    )

    return best_dish, worst_dish, explanations
def generate_insights():

    import sqlite3
    import statistics

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # ---------------------------------
    # ATTENDANCE (Per-Day Based)
    # ---------------------------------
    cursor.execute("""
        SELECT attendance_date, meal_type, COUNT(*)
        FROM attendance
        GROUP BY attendance_date, meal_type
        ORDER BY attendance_date
    """)
    rows = cursor.fetchall()

    # Count distinct days
    cursor.execute("""
        SELECT COUNT(DISTINCT attendance_date)
        FROM attendance
    """)
    total_days = cursor.fetchone()[0] or 0

    if not rows:
        conn.close()
        return {}, {}, None, None, 0, 0, 0, 0, 0

    # Organize meal-wise counts
    meal_data = {}
    daily_totals = {}

    for date, meal, count in rows:
        meal_data.setdefault(meal, []).append(count)
        daily_totals.setdefault(date, 0)
        daily_totals[date] += count

    attendance_data = {}
    attendance_summary = {}
    top_meal = None
    max_avg = 0

    # Compute average per meal (NOT cumulative)
    for meal, counts in meal_data.items():
        avg = sum(counts) / len(counts)
        attendance_data[meal] = round(avg, 2)

        if avg > max_avg:
            max_avg = avg
            top_meal = meal

    total_avg = sum(attendance_data.values())

    for meal, avg in attendance_data.items():
        percentage = round((avg / total_avg) * 100, 1) if total_avg else 0
        attendance_summary[meal] = percentage

    # ---------------------------------
    # Growth Rate (%)
    # ---------------------------------
    growth_rate = 0

    daily_values = list(daily_totals.values())

    if len(daily_values) >= 2:
        first_day = daily_values[0]
        last_day = daily_values[-1]

        if first_day > 0:
            growth_rate = round(((last_day - first_day) / first_day) * 100, 2)

    # ---------------------------------
    # Volatility Score (Std Dev)
    # ---------------------------------
    volatility_score = 0

    if len(daily_values) >= 2:
        volatility_score = round(statistics.stdev(daily_values), 2)

    # ---------------------------------
    # DISH ANALYSIS
    # ---------------------------------
    cursor.execute("""
        SELECT dish.name,
               AVG(rating.rating_value),
               COUNT(rating.rating_id)
        FROM rating
        JOIN dish ON rating.dish_id = dish.dish_id
        GROUP BY dish.name
        ORDER BY AVG(rating.rating_value) DESC
    """)
    rating_rows = cursor.fetchall()

    top_dish = None
    top_rating = 0
    worst_dish = None
    worst_rating = 5
    dish_risk_score = 0

    if rating_rows:
        top_dish = rating_rows[0][0]
        top_rating = round(rating_rows[0][1], 2)

        for name, avg, count in rating_rows:
            if avg < worst_rating:
                worst_rating = avg
                worst_dish = name

        # Risk score (0 to 1 scale)
        dish_risk_score = round((5 - worst_rating) / 5, 2)

    conn.close()

    return (
        attendance_data,
        attendance_summary,
        top_meal,
        top_dish,
        top_rating,
        total_days,
        growth_rate,
        volatility_score,
        dish_risk_score
    )