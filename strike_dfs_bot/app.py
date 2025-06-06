from flask import Flask, request, jsonify
import uuid
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)
STORE_FILE = "token_store.json"

# Load token store from file
def load_store():
    if not os.path.exists(STORE_FILE):
        return {}
    with open(STORE_FILE, "r") as f:
        return json.load(f)

# Save token store to file
def save_store(data):
    with open(STORE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Create a new token
@app.route("/generate_token", methods=["POST"])
def generate_token():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    token = str(uuid.uuid4())[:8]
    expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

    store = load_store()
    store[token] = {
        "user_id": user_id,
        "expires_at": expires_at
    }
    save_store(store)

    return jsonify({
        "token": token,
        "expires_at": expires_at
    })

# Verify the token
@app.route("/api/discord/verify", methods=["GET"])
def verify_token():
    token = request.args.get("token")
    store = load_store()

    record = store.get(token)
    if not record:
        return jsonify({"success": False, "reason": "invalid token"}), 404

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.utcnow() > expires_at:
        return jsonify({"success": False, "reason": "token expired"}), 403

    # Optional: remove token after verification
    del store[token]
    save_store(store)

    return jsonify({
        "success": True,
        "user_id": record["user_id"],
        "username": f"{record['user_id']}@strike.app"
    })

# Health check
@app.route("/")
def home():
    return "✅ Strike Auth Backend is running."


if __name__ == "__main__":
    app.run(debug=True)