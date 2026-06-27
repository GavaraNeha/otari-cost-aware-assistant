# ⚡ Otari – Cost-Aware AI Assistant

> HackArena 2.0 Grand Finale | Mozilla.ai Track | Team: procastiNOTers

## 🚀 What is Otari?
Otari is an intelligent AI assistant that makes smart runtime decisions to optimize cost, security, and performance. Instead of blindly sending every query to an expensive model, Otari analyzes each prompt and routes it to the most cost-effective model.

## ✨ Features
- 🧠 **Dynamic Model Routing** — Complexity scoring routes simple queries to fast cheap models, complex ones to powerful models
- 💰 **Budget Awareness** — Operates within $2 budget, tracks every request
- 🛡️ **Prompt Injection Protection** — Detects and blocks malicious prompts with risk scoring
- 📊 **Usage Transparency** — Shows model used, cost, complexity score, routing reason
- 🔬 **Route Simulator** — See exactly how Otari routes your prompt before sending
- 📈 **Analytics Dashboard** — Real-time cost tracking and request history
- 🎙️ **Voice Integration** — powered by smallest.ai TTS

## 🛠️ Tech Stack
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **AI/Voice:** smallest.ai (Electron LLM + Lightning TTS)
- **Security:** Custom prompt injection detection engine

## 🏃 How to Run
```bash
cd backend
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## 👥 Team
- Gavara Neha
- Gundu Iswarya Lakshmi  
- Ganesam Parthasaradhi Reddy
- Vanka Namratha Amanigreeva

## 🏆 HackArena 2.0 | IIIT Delhi | June 2026