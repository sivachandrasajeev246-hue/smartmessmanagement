import sqlite3
from datetime import datetime, timedelta


def predict_attendance():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    # Count distinct days with data
    cursor.execute("""
        SELECT COUNT(DISTINCT attendance_date)
        FROM attendance
        WHERE attendance_date BETWEEN ? AND ?
    """, (week_ago, today))

    days_with_data = cursor.fetchone()[0]

    if days_with_data == 0:
        conn.close()
        return {
            "breakfast": 0,
            "lunch": 0,
            "dinner": 0
        }, ["⚠ Not enough historical data to generate prediction"]

    # Get total counts
    cursor.execute("""
        SELECT meal_type, COUNT(*)
        FROM attendance
        WHERE attendance_date BETWEEN ? AND ?
        GROUP BY meal_type
    """, (week_ago, today))

    data = cursor.fetchall()
    conn.close()

    predictions = {
        "breakfast": 0,
        "lunch": 0,
        "dinner": 0
    }

    for meal, count in data:
        predictions[meal] = round(count / days_with_data)

    explanations = [
        f"📊 Based on {days_with_data} day(s) of historical attendance data"
    ]

    if datetime.now().weekday() < 5:
        explanations.append("📅 Weekday detected — attendance usually higher")

    if predictions["lunch"] > predictions["breakfast"]:
        explanations.append("🍛 Lunch historically has higher participation")

    return predictions, explanations