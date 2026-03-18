from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import render_template
import sqlite3
import os

app = Flask(__name__)
CORS(app)

print("RomCom APP STARTED")


# ========== DB INIT ==========
# Runs on every startup — creates tables if they don't exist yet
def init_db():
    db_path = os.path.join(os.getcwd(), "users.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT,
            email    TEXT,
            phone    TEXT UNIQUE,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            user_id    TEXT PRIMARY KEY,
            tropes     TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_movies (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            title   TEXT,
            trope   TEXT,
            poster  TEXT,
            rating  TEXT,
            UNIQUE(user_id, title)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialised")

# Call init_db once when the app starts
init_db()


# ========== DB HELPER ==========
def get_db_connection():
    db_path = os.path.join(os.getcwd(), "users.db")
    return sqlite3.connect(db_path)


# ========== PAGE ROUTES ==========
@app.route("/")
def home():
    return render_template("home1.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/signup-page")
def signup_page():
    return render_template("signup.html")

@app.route("/main-page")
def main_page():
    return render_template("main.html")

@app.route("/preferences-page")
def preferences_page():
    return render_template("preferences.html")

# ✅ NEW — was missing, referenced in main.html watchlist button
@app.route("/watchlist-page")
def watchlist_page():
    return render_template("watchlist.html")


# ========== SIGNUP ==========
def save_user(name, email, phone, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, phone, password)
        VALUES (?, ?, ?, ?)
    """, (name, email, phone, password))
    conn.commit()
    conn.close()

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name     = data.get("name")
    email    = data.get("email")
    phone    = data.get("phone")
    password = data.get("password")

    try:
        save_user(name, email, phone, password)
        return jsonify({"message": "User registered successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "Phone already registered"}), 400


# ========== LOGIN ==========
@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    phone    = data.get("phone")
    password = data.get("password")

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE phone = ? AND password = ?",
        (phone, password)
    )
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"message": "Login successful", "phone": phone})
    else:
        return jsonify({"message": "Invalid phone or password"}), 400


# ========== SAVE PREFERENCES ==========
@app.route('/save-preferences', methods=['POST'])
def save_preferences():
    try:
        data    = request.get_json()
        user_id = data.get('user_id')
        tropes  = data.get('tropes', [])

        if not user_id:
            return jsonify({'message': 'User ID is required'}), 400
        if not tropes:
            return jsonify({'message': 'Please select at least one trope'}), 400

        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE preferences
                SET tropes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (','.join(tropes), user_id))
            conn.commit()
            conn.close()
            return jsonify({
                'message': 'Preferences updated successfully!',
                'data': {'user_id': user_id, 'tropes': tropes}
            }), 200
        else:
            cursor.execute("""
                INSERT INTO preferences (user_id, tropes)
                VALUES (?, ?)
            """, (user_id, ','.join(tropes)))
            conn.commit()
            conn.close()
            return jsonify({
                'message': 'Preferences saved successfully!',
                'data': {'user_id': user_id, 'tropes': tropes}
            }), 201

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ========== GET PREFERENCES ==========
@app.route('/get-preferences/<user_id>', methods=['GET'])
def get_preferences(user_id):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, tropes FROM preferences WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            uid, tropes_str = result
            return jsonify({
                'message': 'Preferences found',
                'data': {'user_id': uid, 'tropes': tropes_str.split(',')}
            }), 200
        else:
            return jsonify({'message': 'No preferences found'}), 404

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ========== DELETE PREFERENCES ==========
@app.route('/delete-preferences/<user_id>', methods=['DELETE'])
def delete_preferences(user_id):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute("DELETE FROM preferences WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Preferences deleted successfully'}), 200
        else:
            conn.close()
            return jsonify({'message': 'No preferences found'}), 404

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ========== SAVE MOVIE ==========
@app.route("/save-movie", methods=["POST"])
def save_movie():
    data    = request.get_json()
    user_id = data.get("user_id")
    title   = data.get("title")
    trope   = data.get("trope")
    poster  = data.get("poster", "")
    rating  = data.get("rating", "")

    if not user_id or not title:
        return jsonify({"message": "Missing user_id or title"}), 400

    conn = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO saved_movies (user_id, title, trope, poster, rating)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, title, trope, poster, rating))
        conn.commit()
        return jsonify({"message": "Movie saved to watchlist"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "Movie already saved"}), 400
    except Exception as e:
        return jsonify({"message": "Server error while saving movie"}), 500
    finally:
        if conn:
            conn.close()


# ========== GET SAVED MOVIES ==========
@app.route("/get-saved-movies/<user_id>")
def get_saved_movies(user_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, trope, poster, rating
        FROM saved_movies
        WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify({"saved_movies": [dict(row) for row in rows]})


# ========== REMOVE FROM WATCHLIST ==========
@app.route("/remove-from-watchlist/<user_id>/<title>", methods=["DELETE"])
def remove_from_watchlist(user_id, title):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM saved_movies WHERE user_id = ? AND title = ?
        """, (user_id, title))
        conn.commit()
        conn.close()
        return jsonify({"message": f"'{title}' removed from watchlist"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ========== SEARCH ==========
@app.route("/search", methods=["GET"])
def search_movies():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"found": False})

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, trope, poster, rating
        FROM movies
        WHERE LOWER(title) LIKE LOWER(?)
    """, (f"%{q}%",))
    results = cursor.fetchall()
    conn.close()
    return jsonify({"found": len(results) > 0, "results": [dict(r) for r in results]})


# ========== HEALTH CHECK ==========
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'message': 'RomCom server is running!'}), 200


# ========== START SERVER ==========
# ✅ Render sets $PORT dynamically — must bind to 0.0.0.0
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"RomCom Running on Port {port}")
    app.run(host="0.0.0.0", port=port)