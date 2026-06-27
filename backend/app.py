from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from security import detect_injection
from complexity import analyze_complexity
from budget import check_budget, record_spend, get_stats
from dotenv import load_dotenv
import requests
import os

# -----------------------------
# Frontend Configuration
# -----------------------------
FRONTEND_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../frontend")
)

app = Flask(
    __name__,
    static_folder=FRONTEND_FOLDER,
    static_url_path=""
)

CORS(app)

# -----------------------------
# API Configuration
# -----------------------------
load_dotenv()
SMALLEST_API_KEY = os.getenv("SMALLEST_API_KEY")
SMALLEST_API_URL = "https://api.smallest.ai/v1/chat/completions"


# -----------------------------
# Serve Frontend
# -----------------------------
@app.route("/")
def home():
    return send_from_directory(FRONTEND_FOLDER, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_FOLDER, filename)


# -----------------------------
# Smallest AI Call
# -----------------------------
def call_smallest_ai(prompt, model):
    try:
        headers = {
            "Authorization": f"Bearer {SMALLEST_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = requests.post(
            SMALLEST_API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)

        if response.status_code == 200:
            return response.json()

        return {"error": f"API Error {response.status_code}"}

    except Exception as e:
        print("ERROR:", str(e))
        return {"error": str(e)}


# -----------------------------
# Chat Route
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():

    data = request.json
    prompt = data.get("message", "").strip()

    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    # Security Check
    security = detect_injection(prompt)

    if security["is_threat"]:
        return jsonify({
            "blocked": True,
            "risk_score": security["risk_score"],
            "reason": security["reason"],
            "action": "BLOCKED"
        })

    # Complexity Analysis
    complexity = analyze_complexity(prompt)

    # Budget Check
    budget = check_budget(complexity["cost"])

    if not budget["allowed"]:
        return jsonify({
            "error": "Budget limit reached",
            "spent": budget["spent"],
            "remaining": budget["remaining"]
        })

    # Call Smallest AI
    ai_response = call_smallest_ai(
        prompt,
        complexity["model"]
    )

    # Record Spend
    record_spend(
        complexity["cost"],
        prompt,
        complexity["model"]
    )

    response_text = (
        ai_response.get("choices", [{}])[0]
        .get("message", {})
        .get("content")
        or ai_response.get("output")
        or ai_response.get("text")
        or str(ai_response)
    )

    return jsonify({
        "response": response_text,
        "model_used": complexity["model"],
        "complexity": complexity["level"],
        "complexity_score": complexity["score"],
        "cost": complexity["cost"],
        "budget_remaining": budget["remaining"],
        "security_status": "CLEAN",
        "routing_reason": f"Prompt complexity score: {complexity['score']}/100"
    })


# -----------------------------
# Dashboard Stats
# -----------------------------
@app.route("/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())


# -----------------------------
# Health Check
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "version": "1.0.0"
    })


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )