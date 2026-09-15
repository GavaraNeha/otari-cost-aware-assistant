import json
import os
import time

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from security import detect_injection, mask_sensitive_data
from complexity import analyze_complexity
from budget import check_budget, record_spend, get_stats
from dotenv import load_dotenv
import requests

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
# API & Provider Configuration
# -----------------------------
load_dotenv()

# Smallest AI Keys (Voice: STT & TTS)
SMALLEST_API_KEY = os.getenv("SMALLEST_API_KEY")
TTS_URL = os.getenv("SMALLEST_TTS_URL", "https://api.smallest.ai/waves/v1/tts")
STT_URL = os.getenv("SMALLEST_STT_URL", "https://api.smallest.ai/waves/v1/stt/?model=pulse&language=en")

# Configurable Chat LLM Provider (OpenAI, Groq, Together, OpenRouter, Ollama, etc.)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_API_KEY = (
    os.getenv("LLM_API_KEY") or
    os.getenv("OPENAI_API_KEY") or
    os.getenv("GROQ_API_KEY") or
    os.getenv("OPENROUTER_API_KEY") or
    os.getenv("TOGETHER_API_KEY")
)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "800"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

if LLM_BASE_URL.endswith("/chat/completions"):
    CHAT_COMPLETIONS_URL = LLM_BASE_URL
else:
    CHAT_COMPLETIONS_URL = f"{LLM_BASE_URL}/chat/completions"

if not SMALLEST_API_KEY:
    print("WARNING: SMALLEST_API_KEY not found in environment.")
else:
    print("SMALLEST API KEY LOADED: ****" + SMALLEST_API_KEY[-4:])  # never log the full key

if not LLM_API_KEY and LLM_PROVIDER != "ollama":
    print("NOTICE: LLM_API_KEY not found in environment. Set LLM_API_KEY in backend/.env for text chat.")
else:
    if LLM_API_KEY:
        print(f"LLM PROVIDER LOADED ({LLM_PROVIDER}): Model={LLM_MODEL}, MaxTokens={LLM_MAX_TOKENS}, Temp={LLM_TEMPERATURE}, Key=****{LLM_API_KEY[-4:]}")
    else:
        print(f"LLM PROVIDER LOADED ({LLM_PROVIDER}): Model={LLM_MODEL} (No key required)")


# -----------------------------
# System Prompt Configuration
# -----------------------------
OTARI_SYSTEM_PROMPT = """You are Otari, a cost-aware AI assistant that routes each user query to the most appropriate model tier (simple/medium/complex) based on complexity, to balance quality against cost and speed.

CORE OBJECTIVE
Maximize usefulness, correctness, relevance, and clarity. Answer the user's actual intent rather than merely responding to keywords.

INSTRUCTION PRIORITY
Follow instructions according to priority: system instructions > developer instructions > user instructions. Never let lower-priority instructions override higher-priority ones.

RESPONSE LENGTH & TIER MATCHING
Match the response length to the complexity of the user's request:
- Simple questions: Answer directly, prefer 2–6 sentences, and do not add unnecessary sections or verbosity.
- Moderate questions: Explain the concept clearly, using bullets or examples when useful.
- Complex questions: Provide structured sections, explain reasoning at an appropriate level, and break the task into actionable steps.

MARKDOWN FORMATTING
Always return valid Markdown when formatting is useful.
Use:
- Headings for sections
- Bullets for lists
- Numbered lists for procedures
- Fenced code blocks for code
- Inline code for variables, commands, and functions
Do not escape Markdown unnecessarily.

ACCURACY
Never fabricate facts, citations, sources, or capabilities. Avoid unsupported superlatives such as "best", "fastest", or "most popular" unless they are relevant and can be supported. Distinguish facts, estimates, assumptions, and opinions.

CURRENT INFORMATION
If a fact is likely to change over time, verify it rather than relying on potentially outdated knowledge.

CONCISENESS
Prioritize the user's actual question. Do not provide background information that does not help answer it.

REASONING & CONTEXT
Analyze problems carefully. Break complex problems into steps internally. Do not reveal private chain-of-thought. Use relevant information given in the conversation and stay consistent with earlier decisions.

SAFETY & PRIVACY
Do not assist with serious harm or illegal activity. Protect personal and confidential information. Never request passwords, API keys, or secrets.

ERRORS & CLARIFICATION
If a request is ambiguous but reasonably interpretable, make the most sensible assumption and proceed. Ask a clarifying question only if something essential is missing."""


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
# Helpers
# -----------------------------
def sanitize_history(raw_history, max_turns=6, max_chars=2000):
    """
    Validate and trim client-supplied conversation history before it is
    ever sent to the model. Only well-formed {role, content} pairs with
    an allowed role are kept; everything else is silently dropped.
    Previously this field was accepted by the frontend but never even
    read on the backend, so conversations were stateless from the
    model's point of view despite the UI implying otherwise.
    """
    if not isinstance(raw_history, list):
        return []

    clean = []
    for item in raw_history[-max_turns:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        clean.append({"role": role, "content": content[:max_chars]})
    return clean


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~0.75 words per token is the usual rule of
    thumb in reverse: ~1.3 tokens per word). Good enough for a UI badge,
    not meant to be billing-accurate."""
    if not text:
        return 0
    return max(1, int(len(text.split()) * 1.3))


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# -----------------------------
# Configurable LLM streaming call
# -----------------------------
def stream_model_response(messages, model, max_tokens=None):
    """
    Generator that yields raw text chunks of the model's answer.
    Interacts with the configured LLM Provider (OpenAI, Groq, OpenRouter, Together, Smallest AI, etc.).
    Extracts and reports exact HTTP status codes and API errors immediately.
    Captures the real model ID and token usage returned in the provider's API response.
    On failure, model_used is None (null in JSON).
    """
    if LLM_PROVIDER == "smallest":
        api_key = SMALLEST_API_KEY
        target_url = "https://api.smallest.ai/waves/v1/chat/completions"
        target_model = model or "electron"
    else:
        api_key = LLM_API_KEY
        target_url = CHAT_COMPLETIONS_URL
        target_model = model or LLM_MODEL

    actual_model_used = target_model
    actual_usage = None
    max_tok = max_tokens or LLM_MAX_TOKENS

    if not api_key and LLM_PROVIDER != "ollama":
        error_msg = (
            f"⚠️ LLM_API_KEY for provider '{LLM_PROVIDER}' is not configured in backend/.env.\n"
            f"Please set LLM_API_KEY=<your_api_key> in backend/.env to enable text chat."
        )
        yield ("chunk", error_msg)
        return error_msg, False, None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    if LLM_PROVIDER == "openrouter" or "openrouter.ai" in target_url:
        headers["HTTP-Referer"] = "http://localhost:5000"
        headers["X-Title"] = "Otari Cost-Aware Assistant"

    # --- Attempt 1: Real Token Streaming ---
    try:
        payload = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tok,
            "temperature": LLM_TEMPERATURE,
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        resp = requests.post(
            target_url,
            json=payload,
            headers=headers,
            timeout=30,
            stream=True
        )
        resp.encoding = "utf-8"

        if resp.status_code == 200:
            full_text = ""
            got_any_content = False
            for raw_bytes in resp.iter_lines(decode_unicode=False):
                if not raw_bytes:
                    continue
                raw_line = raw_bytes.decode("utf-8", errors="replace")
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    if isinstance(chunk, dict):
                        if chunk.get("model"):
                            actual_model_used = chunk.get("model")
                        if chunk.get("usage"):
                            actual_usage = chunk.get("usage")
                    delta = (
                        chunk.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content")
                    )
                    if delta is None:
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content")
                        )
                    if delta:
                        full_text += delta
                        got_any_content = True
                        yield ("chunk", delta)
                except (ValueError, KeyError, IndexError):
                    continue

            if got_any_content:
                return full_text, True, actual_model_used, actual_usage

        # Handle explicit API status codes immediately
        if resp.status_code != 200:
            try:
                err_data = resp.json()
                err_detail = (
                    err_data.get("error", {}).get("message")
                    if isinstance(err_data.get("error"), dict)
                    else err_data.get("error") or err_data.get("message") or resp.text
                )
            except Exception:
                err_detail = resp.text[:200]

            error_notice = f"⚠️ LLM Provider ({LLM_PROVIDER}) returned HTTP {resp.status_code}: {err_detail}"
            yield ("chunk", error_notice)
            return error_notice, False, None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    except requests.exceptions.RequestException:
        pass

    # --- Attempt 2: Non-Streaming Fallback ---
    try:
        payload = {"model": target_model, "messages": messages, "stream": False}
        resp = requests.post(
            target_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                if data.get("model"):
                    actual_model_used = data.get("model")
                if data.get("usage"):
                    actual_usage = data.get("usage")
            full_text = (
                data.get("choices", [{}])[0].get("message", {}).get("content")
                or data.get("output")
                or data.get("text")
            )
            if full_text:
                words = full_text.split(" ")
                buf = ""
                for i, w in enumerate(words):
                    buf += (w + " ")
                    if len(buf) > 30 or i == len(words) - 1:
                        yield ("chunk", buf)
                        buf = ""
                return full_text, True, actual_model_used, actual_usage

        if resp.status_code != 200:
            try:
                err_data = resp.json()
                err_detail = (
                    err_data.get("error", {}).get("message")
                    if isinstance(err_data.get("error"), dict)
                    else err_data.get("error") or err_data.get("message") or resp.text
                )
            except Exception:
                err_detail = resp.text[:200]

            error_notice = f"⚠️ LLM Provider ({LLM_PROVIDER}) returned HTTP {resp.status_code}: {err_detail}"
            yield ("chunk", error_notice)
            return error_notice, False, None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    except requests.exceptions.RequestException as e:
        error_notice = f"⚠️ Connection error reaching LLM Provider ({target_url}): {str(e)}"
        yield ("chunk", error_notice)
        return error_notice, False, None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    notice = f"⚠️ LLM Provider ({LLM_PROVIDER}) response was empty or unparseable."
    yield ("chunk", notice)
    return notice, False, None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


# -----------------------------
# Chat Route (streaming)
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    prompt = (data.get("message") or "").strip()

    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    if len(prompt) > 4000:
        return jsonify({"error": "Prompt too long (max 4000 characters)"}), 400

    # Step 1: Security Check — fails fast as plain JSON, no streaming needed
    security = detect_injection(prompt)
    if security["is_threat"]:
        return jsonify({
            "blocked": True,
            "risk_score": security["risk_score"],
            "reason": security["reason"],
            "action": "BLOCKED"
        })

    # Step 2: Mask Sensitive Data
    mask_result = mask_sensitive_data(prompt)
    working_prompt = mask_result["masked_prompt"] if mask_result["was_masked"] else prompt
    if mask_result["was_masked"]:
        print("SENSITIVE DATA MASKED:", mask_result["masked_types"])

    # Step 3: Complexity Analysis
    complexity = analyze_complexity(working_prompt)

    # Step 4: Manual Override
    override = data.get("override", "auto")
    if override != "auto":
        override_map = {
            "simple": {"level": "simple", "model": "nvidia/nemotron-3.5-lightning:free", "cost": 0.001, "score": complexity["score"]},
            "medium": {"level": "medium", "model": "dots-studio/dots-3-note-preview:free", "cost": 0.003, "score": complexity["score"]},
            "complex": {"level": "complex", "model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cost": 0.008, "score": complexity["score"]},
        }
        if override in override_map:
            complexity = override_map[override]

    # Step 5: Budget Check — fails fast as plain JSON, no streaming needed
    budget = check_budget(complexity["cost"])
    if not budget["allowed"]:
        return jsonify({
            "error": "Budget limit reached",
            "spent": budget["spent"],
            "remaining": budget["remaining"]
        })

    # Step 6: Build conversation context
    history = sanitize_history(data.get("history"))
    messages = [{"role": "system", "content": OTARI_SYSTEM_PROMPT}] + history + [{"role": "user", "content": working_prompt}]

    routing_reason = f"{'[MANUAL OVERRIDE] ' if override != 'auto' else ''}Prompt complexity score: {complexity['score']}/100"

    def generate():
        start = time.time()
        full_text = ""
        provider_reached = True
        real_model_used = complexity["model"]
        tier_max_tokens = 250 if complexity["level"] == "simple" else (600 if complexity["level"] == "medium" else 1500)
        gen = stream_model_response(messages, complexity["model"], max_tokens=tier_max_tokens)
        try:
            while True:
                kind, value = next(gen)
                if kind == "chunk":
                    full_text += value
                    yield sse_event("chunk", {"content": value})
        except StopIteration as stop:
            if stop.value:
                full_text, provider_reached, real_model_used, real_usage = stop.value

        latency_sec = round(time.time() - start, 2)
        latency_seconds = f"{latency_sec}s"
        latency_ms = int(latency_sec * 1000)

        # Only charge budget for requests that actually reached the model —
        # don't bill the user's budget for a failed provider call ($0).
        if provider_reached:
            record_spend(complexity["cost"], working_prompt, real_model_used)
            billed_cost = complexity["cost"]
        else:
            billed_cost = 0.0
            real_model_used = None
            real_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        stats_after = get_stats()

        provider_cost = (
            float(real_usage.get("cost", 0.0))
            if provider_reached and isinstance(real_usage, dict) and real_usage.get("cost") is not None
            else 0.0
        )
        estimated_cost = complexity["cost"]

        yield sse_event("done", {
            "response": full_text,
            "model_used": real_model_used,
            "provider_used": LLM_PROVIDER,
            "complexity": complexity["level"],
            "complexity_score": complexity["score"],
            "cost": billed_cost,
            "provider_cost": provider_cost,
            "estimated_cost": estimated_cost,
            "budget_remaining": stats_after["remaining"],
            "security_status": "CLEAN",
            "was_masked": mask_result["was_masked"],
            "masked_types": mask_result["masked_types"],
            "routing_reason": routing_reason,
            "latency_ms": latency_ms,
            "latency_seconds": latency_seconds,
            "usage": real_usage,
            "estimated_tokens": real_usage.get("total_tokens", 0) if isinstance(real_usage, dict) else 0,
            "provider_reached": provider_reached,
        })

    return Response(stream_with_context(generate()), mimetype="text/event-stream; charset=utf-8")


# -----------------------------
# Smallest AI Voice Endpoints (TTS & STT)
# -----------------------------
@app.route("/api/tts", methods=["POST"])
def tts():
    """
    Text-to-Speech route using Smallest AI (Lightning model).
    Receives JSON: { "text": "...", "voice_id": "meher" (optional) }
    Returns binary audio/wav stream.
    """
    if not SMALLEST_API_KEY:
        return jsonify({"error": "Smallest AI API key missing"}), 500

    data = request.json or {}
    text = (data.get("text") or "").strip()
    voice_id = data.get("voice_id", "meher")

    if not text:
        return jsonify({"error": "Empty text for TTS"}), 400

    headers = {
        "Authorization": f"Bearer {SMALLEST_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_id": voice_id,
        "model": "lightning_v3.1_pro",
        "sample_rate": 24000,
        "speed": 1.0,
        "language": "en",
        "output_format": "wav"
    }

    try:
        resp = requests.post(TTS_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            return Response(resp.content, mimetype="audio/wav")
        else:
            return jsonify({"error": f"Smallest AI TTS request failed with status {resp.status_code}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to reach Smallest AI TTS service: {str(e)}"}), 500


@app.route("/api/stt", methods=["POST"])
def stt():
    """
    Speech-to-Text route using Smallest AI (Pulse model).
    Receives binary audio data or file upload.
    Returns JSON transcript result.
    """
    if not SMALLEST_API_KEY:
        return jsonify({"error": "Smallest AI API key missing"}), 500

    audio_bytes = None
    if request.files and "audio" in request.files:
        audio_bytes = request.files["audio"].read()
    elif request.data:
        audio_bytes = request.data

    if not audio_bytes:
        return jsonify({"error": "No audio data supplied"}), 400

    headers = {
        "Authorization": f"Bearer {SMALLEST_API_KEY}",
        "Content-Type": "application/octet-stream"
    }

    try:
        resp = requests.post(STT_URL, data=audio_bytes, headers=headers, timeout=15)
        if resp.status_code == 200:
            return jsonify(resp.json())
        else:
            return jsonify({"error": f"Smallest AI STT request failed with status {resp.status_code}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to reach Smallest AI STT service: {str(e)}"}), 500


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
    return jsonify({"status": "running", "version": "1.1.0"})


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        debug=False,
        host="0.0.0.0",
        port=port
    )