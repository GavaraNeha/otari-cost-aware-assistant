const API = 'http://localhost:5000';
let conversationHistory = [];

function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
  if (id === 'dashboard') loadStats();
}

async function sendMessage() {
  const input = document.getElementById('userInput');
  const override = document.getElementById('modelOverride').value;
  const msg = input.value.trim();
  if (!msg) return;

  appendMessage(msg, 'user');
  input.value = '';
  document.getElementById('thinking').style.display = 'flex';

  try {
    const res = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        override: override,
        history: conversationHistory.slice(-6)
      })
    });
    const data = await res.json();
    document.getElementById('thinking').style.display = 'none';

    if (data.blocked) {
      appendBlocked(data);
    } else if (data.error) {
      appendMessage(`⚠️ ${data.error}`, 'bot');
    } else {
      appendBot(data);
      updateBudget(data.budget_remaining);
      // Store in conversation history
      conversationHistory.push(
        { role: "user", content: msg },
        { role: "assistant", content: data.response }
      );
    }
  } catch (e) {
    document.getElementById('thinking').style.display = 'none';
    appendMessage('❌ Backend not running. Start Flask server!', 'bot');
  }
}

function appendMessage(text, type) {
  const box = document.getElementById('chatBox');
  const div = document.createElement('div');
  div.className = `message ${type}`;
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function appendBot(data) {
  const box = document.getElementById('chatBox');
  const div = document.createElement('div');
  div.className = 'message bot';

  const maskedBadge = data.was_masked
    ? `&nbsp;|&nbsp; 🔒 Masked: <b>${data.masked_types.join(', ')}</b>`
    : '';

  const overrideBadge = data.routing_reason.includes('MANUAL OVERRIDE')
    ? `&nbsp;|&nbsp; 🎛️ <b>Manual Override</b>`
    : '';

  div.innerHTML = `
    <div>${data.response}</div>
    <div class="meta">
      🤖 Model: <b>${data.model_used}</b> &nbsp;|&nbsp;
      🧠 Complexity: <b>${data.complexity}</b> (${data.complexity_score}/100) &nbsp;|&nbsp;
      💰 Cost: <b>$${data.cost}</b> &nbsp;|&nbsp;
      💵 Remaining: <b>$${data.budget_remaining}</b>
      ${maskedBadge}
      ${overrideBadge}
    </div>
    <div class="meta">📡 ${data.routing_reason}</div>
  `;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function appendBlocked(data) {
  const box = document.getElementById('chatBox');
  const div = document.createElement('div');
  div.className = 'message blocked';
  div.innerHTML = `
    🚫 <b>BLOCKED</b><br>
    ⚠️ ${data.reason}<br>
    <div class="meta">Risk Score: ${data.risk_score}/100 | Action: ${data.action}</div>
  `;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function updateBudget(remaining) {
  const pct = (remaining / 2.0) * 100;
  const bar = document.getElementById('budgetBar');
  const text = document.getElementById('budgetText');
  bar.style.width = pct + '%';
  bar.style.background = pct > 50 ? '#00ff88' : pct > 25 ? '#ffaa00' : '#ff4444';
  text.style.color = pct > 50 ? '#00ff88' : pct > 25 ? '#ffaa00' : '#ff4444';
  text.textContent = `$${remaining.toFixed(4)} remaining`;
}

async function loadStats() {
  try {
    const res = await fetch(`${API}/stats`);
    const data = await res.json();
    document.getElementById('statSpent').textContent = `$${data.spent}`;
    document.getElementById('statRemaining').textContent = `$${data.remaining}`;
    document.getElementById('statRequests').textContent = data.requests;

    const log = document.getElementById('requestLog');
    log.innerHTML = '<h3 style="color:#aaa;margin-bottom:12px">Request History</h3>';
    data.log.forEach((item, i) => {
      log.innerHTML += `
        <div class="log-item">
          <span>#${i+1} — ${item.prompt_preview}...</span>
          <span class="log-model">${item.model}</span>
          <span class="log-cost">$${item.cost}</span>
        </div>`;
    });
  } catch (e) {
    console.log('Stats error:', e);
  }
}

async function simulate() {
  const input = document.getElementById('simInput').value.trim();
  if (!input) return;

  const words = input.split(' ').length;
  const complexKeywords = ['explain','analyze','compare','calculate','code',
    'write','build','design','create','implement','difference','how','why','summarize'];
  const hits = complexKeywords.filter(k => input.toLowerCase().includes(k)).length;
  const score = Math.min(100, (words * 2) + (hits * 15));

  const threats = ['ignore previous','system prompt','jailbreak',
    'forget instructions','you are now','act as','bypass','override'];
  const threat = threats.find(t => input.toLowerCase().includes(t));

  const level = score < 30 ? 'Simple' : score < 65 ? 'Medium' : 'Complex';
  const model = score < 30 ? 'electron-fast' : score < 65 ? 'electron-balanced' : 'electron-pro';
  const cost = score < 30 ? 0.001 : score < 65 ? 0.003 : 0.008;
  const gpt4cost = 0.03;

  const result = document.getElementById('simResult');
  result.style.display = 'block';
  result.innerHTML = `
    <div class="sim-step">
      <div class="sim-icon">🔍</div>
      <div class="sim-label">Security Check</div>
      <div class="sim-value ${threat ? 'red' : ''}">${threat ? '🚫 BLOCKED — ' + threat : '✅ CLEAN'}</div>
    </div>
    <div class="sim-step">
      <div class="sim-icon">🧠</div>
      <div class="sim-label">Complexity Score</div>
      <div class="sim-value yellow">${score}/100 — ${level}</div>
    </div>
    <div class="sim-step">
      <div class="sim-icon">📡</div>
      <div class="sim-label">Model Selected</div>
      <div class="sim-value">${model}</div>
    </div>
    <div class="sim-step">
      <div class="sim-icon">💰</div>
      <div class="sim-label">Estimated Cost</div>
      <div class="sim-value">$${cost} <span style="color:#555;font-size:11px">(GPT-4 would cost $${gpt4cost})</span></div>
    </div>
    <div class="sim-step">
      <div class="sim-icon">📉</div>
      <div class="sim-label">Cost Saved</div>
      <div class="sim-value">${Math.round((1 - cost/gpt4cost)*100)}% cheaper than GPT-4</div>
    </div>
  `;
}

// Load budget on start
updateBudget(2.0);