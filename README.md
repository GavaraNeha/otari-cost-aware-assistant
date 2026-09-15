# ⚡ Otari – Cost-Aware AI Assistant

> **HackArena 2.0 Grand Finale** | **Mozilla.ai Track** | **Team: procastiNOTers**

Otari is an intelligent, cost-aware AI assistant that dynamically routes incoming user queries to appropriate LLM complexity tiers, balancing output quality against cost and latency.

---

## 🚀 Key Features

- 🧠 **Dynamic Complexity Classification**  
  Analyzes query intent, domain concepts, technical depth, and multi-step requirements to route queries automatically to the appropriate complexity tier:
  - **Simple Tier**: Fast, concise answers (`nvidia/nemotron-3.5-lightning:free`)
  - **Medium Tier**: Balanced conceptual explanations (`dots-studio/dots-3-note-preview:free`)
  - **Complex Tier**: Systems architecture & multi-step engineering (`nvidia/nemotron-3-ultra-550b-a55b:free`)

- 💰 **Transparent Cost & Budget Accounting**  
  - Operates within a customizable budget (default `$2.00`).
  - Separates actual **Provider Cost** (`$0.0000` for free models) from internal **Tier Estimate** and **Billed Budget** cost.
  - Zero-cost/zero-token guarantee on provider failures ($0 billed to budget).

- 🔤 **Real Token Usage & Metadata Details**  
  Displays real OpenRouter usage metrics (`prompt_tokens`, `completion_tokens`, `total_tokens`), exact responding model ID, request latency in seconds, and routing notes inside an expandable `▸ Response details` panel.

- 📝 **Live Markdown & Token Streaming**  
  Streams responses token-by-token using Server-Sent Events (SSE) and renders real HTML (headings, bold text, lists, fenced code blocks, tables) with client-side UTF-8 encoding.

- 🛡️ **Prompt Injection & Sensitive Data Guardrails**  
  Identifies malicious prompt injection attacks, evaluates risk scores, and masks sensitive data patterns prior to model invocation.

- 🎙️ **Voice Controls (STT & TTS)**  
  Speech-to-Text and Text-to-Speech powered by Smallest AI (`pulse` STT & `lightning_v3.1_pro` TTS).

- 📊 **Analytics Dashboard & Route Simulator**  
  Interactive simulator to dry-run complexity scores and live request history logs.

---

## 🛠️ Architecture & Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), `marked.js`
- **Backend**: Python 3.10+, Flask, `flask-cors`, `requests`, `python-dotenv`
- **LLM Provider**: OpenRouter API (`nvidia/nemotron-3.5-lightning:free`, `dots-studio/dots-3-note-preview:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`)
- **Voice Provider**: Smallest AI (`Waves API` TTS & STT)

---

## 📁 Repository Structure

```text
otari-cost-aware-assistant/
├── backend/
│   ├── app.py           # Main Flask API, SSE streaming & chat endpoints
│   ├── budget.py        # Budget tracking & spend recorder
│   ├── complexity.py    # Query complexity classifier & scoring engine
│   ├── router.py        # Model tier router
│   ├── security.py      # Injection detector & data masking engine
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── index.html       # Single-page UI layout
│   ├── app.js           # Client-side streaming logic & response details grid
│   └── style.css        # UI theme & Markdown styling
├── .env.example         # Environment variables template
└── README.md            # Project documentation
```

---

## 🏃 How to Run Locally

### 1. Prerequisites
- Python 3.10+
- OpenRouter API Key (or optional OpenAI / Groq / Ollama setup)

### 2. Setup Environment
Clone the repository and create your `backend/.env` file:
```bash
cp .env.example backend/.env
```

Add your API keys in `backend/.env`:
```env
LLM_PROVIDER=openrouter
LLM_API_KEY=your_openrouter_api_key
SMALLEST_API_KEY=your_smallest_ai_key
```

### 3. Install & Run
```bash
cd backend
pip install -r requirements.txt
python app.py
```

Open your browser and navigate to:
**[http://localhost:5000](http://localhost:5000)**

---

## 👥 Team: procastiNOTers

- **Gavara Neha**
- **Gundu Iswarya Lakshmi**
- **Ganesam Parthasaradhi Reddy**
- **Vanka Namratha Amanigreeva**

---

## 🏆 Event

**HackArena 2.0 | IIIT Delhi | Mozilla.ai Track**