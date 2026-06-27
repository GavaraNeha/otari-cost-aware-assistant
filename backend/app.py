from flask import Flask, request, jsonify
from flask_cors import CORS
from security import detect_injection
from complexity import analyze_complexity
from budget import check_budget, record_spend, get_stats
import requests
import os

app = Flask(__name__)
CORS(app)

SMALLEST_API_KEY = os.getenv("SMALLEST_API_KEY", "your-api-key-here")
SMALLEST_API_URL = "https://api.smallest.ai/v1/chat"

def call_smallest_ai(prompt, model):
    try:
        headers = {
            "Authorization": f"Bearer {SMALLEST_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(SMALLEST_API_URL, 
                                json=payload, 
                                headers=headers, 
                                timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('message', '').strip()

    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    # Step 1: Security check
    security = detect_injection(prompt)
    if security["is_threat"]:
        return jsonify({
            "blocked": True,
            "risk_score": security["risk_score"],
            "reason": security["reason"],
            "action": "BLOCKED"
        })

    # Step 2: Complexity analysis
    complexity = analyze_complexity(prompt)

    # Step 3: Budget check
    budget = check_budget(complexity["cost"])
    if not budget["allowed"]:
        return jsonify({
            "error": "Budget limit reached",
            "spent": budget["spent"],
            "remaining": budget["remaining"]
        })

    # Step 4: Call smallest.ai
    ai_response = call_smallest_ai(prompt, complexity["model"])

    # Step 5: Record spend
    record_spend(complexity["cost"], prompt, complexity["model"])

    return jsonify({
        "response": ai_response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "Response received"),
        "model_used": complexity["model"],
        "complexity": complexity["level"],
        "complexity_score": complexity["score"],
        "cost": complexity["cost"],
        "budget_remaining": budget["remaining"],
        "security_status": "CLEAN",
        "routing_reason": f"Prompt complexity score: {complexity['score']}/100"
    })

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify(get_stats())

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "running", "version": "1.0.0"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)