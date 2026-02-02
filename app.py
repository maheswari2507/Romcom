from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import sqlite3

app = Flask(__name__)
CORS(app)

otp_store = {}

print("🎬 RomCom APP STARTED")

# ---------- DB ----------
def get_db_connection():
    return sqlite3.connect("users.db")

def save_user(name, email, phone, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, phone, password)
        VALUES (?, ?, ?, ?)
    """, (name, email, phone, password))
    conn.commit()
    conn.close()

# ---------- SEND OTP ----------
@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    phone = data.get("phone")

    if not phone:
        return jsonify({"message": "Phone number missing"}), 400

    otp = random.randint(1000, 9999)
    otp_store[phone] = otp

    print(f"📱 OTP for {phone} is {otp}")

    return jsonify({"message": "OTP sent successfully"})

# ---------- VERIFY OTP + SIGNUP ----------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")
    user_otp = data.get("otp")

    if phone not in otp_store:
        return jsonify({"message": "OTP not sent"}), 400

    if str(otp_store[phone]) != str(user_otp):
        return jsonify({"message": "Invalid OTP"}), 400

    try:
        save_user(name, email, phone, password)
        del otp_store[phone]
        return jsonify({"message": "User registered successfully 🎉"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "Phone already registered"}), 400

# ---------- LOGIN ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    phone = data.get("phone")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE phone = ? AND password = ?",
        (phone, password)
    )

    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"message": "Login successful 🎉", "phone": phone})
    else:
        return jsonify({"message": "Invalid phone or password"}), 400
    
# ---------- SAVE PREFERENCES ----------
@app.route('/save-preferences', methods=['POST'])
def save_preferences():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        tropes = data.get('tropes', [])

        if not user_id:
            return jsonify({'message': 'User ID is required'}), 400
        
        if not tropes or len(tropes) == 0:
            return jsonify({'message': 'Please select at least one trope'}), 400

        conn = get_db_connection()
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
            print(f"✅ Updated preferences for user: {user_id}")
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
            print(f"✅ Saved new preferences for user: {user_id}")
            return jsonify({
                'message': 'Preferences saved successfully!',
                'data': {'user_id': user_id, 'tropes': tropes}
            }), 201

    except Exception as e:
        print(f"❌ Error saving preferences: {str(e)}")
        return jsonify({'message': f'Error: {str(e)}'}), 500

# ---------- GET PREFERENCES ----------
@app.route('/get-preferences/<user_id>', methods=['GET'])
def get_preferences(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, tropes FROM preferences WHERE user_id = ?", (user_id,))
        
        result = cursor.fetchone()
        conn.close()

        if result:
            user_id, tropes_str = result
            tropes_list = tropes_str.split(',')
            print(f"✅ Retrieved preferences for user: {user_id}")
            return jsonify({
                'message': 'Preferences found',
                'data': {'user_id': user_id, 'tropes': tropes_list}
            }), 200
        else:
            print(f"⚠️ No preferences found for user: {user_id}")
            return jsonify({'message': 'No preferences found'}), 404

    except Exception as e:
        print(f"❌ Error retrieving preferences: {str(e)}")
        return jsonify({'message': f'Error: {str(e)}'}), 500

# ---------- DELETE PREFERENCES ----------
@app.route('/delete-preferences/<user_id>', methods=['DELETE'])
def delete_preferences(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
        
        result = cursor.fetchone()
        
        if result:
            cursor.execute("DELETE FROM preferences WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            print(f"✅ Deleted preferences for user: {user_id}")
            return jsonify({'message': 'Preferences deleted successfully'}), 200
        else:
            conn.close()
            print(f"⚠️ No preferences found to delete for user: {user_id}")
            return jsonify({'message': 'No preferences found'}), 404

    except Exception as e:
        print(f"❌ Error deleting preferences: {str(e)}")
        return jsonify({'message': f'Error: {str(e)}'}), 500
    
# ---------- SAVE MOVIE ----------
@app.route("/get-saved-movies/<user_id>")
def get_saved_movies(user_id):
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, trope, poster, rating
        FROM saved_movies
        WHERE user_id = ?
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "saved_movies": [dict(row) for row in rows]
    })

# ---------- REMOVE FROM WATCHLIST ----------
@app.route("/remove-from-watchlist/<user_id>/<title>", methods=["DELETE"])
def remove_from_watchlist(user_id, title):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM saved_movies WHERE user_id = ? AND title = ?
        """, (user_id, title))

        conn.commit()
        conn.close()

        print(f"✅ Removed from watchlist: {title}")
        return jsonify({"message": f"'{title}' removed from watchlist"}), 200

    except Exception as e:
        print(f"❌ Error removing movie: {str(e)}")
        return jsonify({"message": str(e)}), 500
@app.route("/search", methods=["GET"])
def search_movies():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify({"found": False})

    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, trope, poster, rating
        FROM movies
        WHERE LOWER(title) LIKE LOWER(?)
    """, (f"%{q}%",))

    results = cursor.fetchall()
    conn.close()

    return jsonify({
        "found": len(results) > 0,
        "results": [dict(r) for r in results]
    })


# ---------- HEALTH CHECK ----------
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'message': '🎬 RomCom server is running!'}), 200

# ---------- START SERVER ----------
if __name__ == "__main__":
    print("=" * 50)
    print("🎬 RomCom Running on Port 5000")
    print("=" * 50)
    app.run(debug=True, port=5000)