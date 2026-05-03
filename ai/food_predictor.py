import sqlite3

def predict_top_dish():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.name, AVG(r.rating_value), COUNT(r.rating_value)
        FROM rating r
        JOIN dish d ON r.dish_id = d.dish_id
        GROUP BY r.dish_id
        HAVING COUNT(r.rating_value) >= 3
        ORDER BY AVG(r.rating_value) DESC
        LIMIT 1
    """)

    result = cursor.fetchone()
    conn.close()

    if not result:
        return None, ["Not enough rating data available"]

    dish_name, avg_rating, total_ratings = result

    explanation = [
        f"⭐ Average rating: {round(avg_rating, 2)}",
        f"📊 Based on {total_ratings} user ratings",
        "🔎 Only dishes with at least 3 ratings are considered"
    ]

    return dish_name, explanation