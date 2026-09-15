const API = 'http://localhost:5000';
let conversationHistory = [];

function showSection(id, btn) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn, .nav-link-btn').forEach(b => b.classList.remove('active'));
  
  const target = document.getElementById(id);
  if (target) {
    target.classList.add('active');
  }
  
  if (btn) btn.classList.add('active');
  if (id === 'dashboard') loadStats();
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleHeroSend() {
  const heroInput = document.getElementById('heroInput');
  const text = heroInput ? heroInput.value.trim() : '';
  if (!text) return;

  const userInput = document.getElementById('userInput');
  if (userInput) {
    userInput.value = text;
  }
  heroInput.value = '';

  showSection('chat');
  sendMessage();
}

function renderLogoRays() {
  const raysGroup = document.getElementById('logoRays');
  if (!raysGroup) return;
  const center = 26;
  const innerR = 10.4;
  const outerR = 22.6;
  const count = 24;
  let lines = '';
  for (let i = 0; i < count; i++) {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI / count);
    const x1 = center + innerR * Math.cos(angle);
    const y1 = center + innerR * Math.sin(angle);
    const x2 = center + outerR * Math.cos(angle);
    const y2 = center + outerR * Math.sin(angle);
    lines += `<line x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>`;
  }
  raysGroup.innerHTML = lines;
}

function toggleMobileMenu() {
  const overlay = document.getElementById('navOverlay');
  const burger = document.getElementById('burgerBtn');
  const isOpen = overlay && overlay.classList.contains('open');
  if (isOpen) {
    closeMobileMenu();
  } else {
    if (overlay) overlay.classList.add('open');
    document.body.classList.add('menu-open');
    if (burger) burger.setAttribute('aria-expanded', 'true');
  }
}

function closeMobileMenu() {
  const overlay = document.getElementById('navOverlay');
  const burger = document.getElementById('burgerBtn');
  if (overlay) overlay.classList.remove('open');
  document.body.classList.remove('menu-open');
  if (burger) burger.setAttribute('aria-expanded', 'false');
}

async function sendMessage() {
  const input = document.getElementById('userInput');
  const override = document.getElementById('modelOverride').value;
  const msg = input.value.trim();
  if (!msg) return;

  appendMessage(msg, 'user');
  input.value = '';

  document.getElementById('thinking').style.display = 'flex';
  document.getElementById('inputArea').classList.add('thinking-active');

  let response;
  try {
    response = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        override: override,
        history: conversationHistory.slice(-6)
      })
    });
  } catch (e) {
    document.getElementById('thinking').style.display = 'none';
    document.getElementById('inputArea').classList.remove('thinking-active');
    appendMessage('❌ Backend not running. Start Flask server!', 'bot');
    return;
  }

  const contentType = response.headers.get('content-type') || '';

  // Blocked prompts / budget errors come back as plain JSON, not a stream
  if (contentType.includes('application/json')) {
    const data = await response.json();
    document.getElementById('thinking').style.display = 'none';
    document.getElementById('inputArea').classList.remove('thinking-active');

    if (data.blocked) {
      appendBlocked(data);
    } else if (data.error) {
      appendMessage(`⚠️ ${data.error}`, 'bot');
    }
    return;
  }

  // Otherwise: stream the response token-by-token via Server-Sent Events
  const shell = createBotMessageShell();
  let firstChunkReceived = false;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop(); // keep the last (possibly incomplete) block for next read

    for (const part of parts) {
      if (!part.trim()) continue;
      const parsed = parseSseBlock(part);
      if (!parsed) continue;

      if (parsed.event === 'chunk') {
        if (!firstChunkReceived) {
          firstChunkReceived = true;
          document.getElementById('thinking').style.display = 'none';
          document.getElementById('inputArea').classList.remove('thinking-active');
        }
        appendBotText(shell, parsed.data.content);
      } else if (parsed.event === 'done') {
        finalizeBotMessage(shell, parsed.data);
        if (parsed.data.provider_reached) {
          conversationHistory.push(
            { role: 'user', content: msg },
            { role: 'assistant', content: parsed.data.response }
          );
        }
        if (typeof parsed.data.budget_remaining === 'number') {
          updateBudget(parsed.data.budget_remaining);
        }
      }
    }
  }

  document.getElementById('thinking').style.display = 'none';
  document.getElementById('inputArea').classList.remove('thinking-active');
}

function parseSseBlock(block) {
  let event = null;
  let data = null;
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim();
    } else if (line.startsWith('data:')) {
      try {
        data = JSON.parse(line.slice('data:'.length).trim());
      } catch (e) {
        return null;
      }
    }
  }
  if (!event || data === null) return null;
  return { event, data };
}

function appendMessage(text, type) {
  const box = document.getElementById('chatBox');
  const div = document.createElement('div');
  div.className = `message ${type}`;
  div.innerHTML = `<div class="bubble"></div>`;
  div.querySelector('.bubble').textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function createBotMessageShell() {
  const box = document.getElementById('chatBox');
  const div = document.createElement('div');
  div.className = 'message bot';
  div.innerHTML = `
    <div class="bubble">
      <div class="bubble-text"></div>
      <div class="meta" style="display:none"></div>
    </div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return {
    el: div,
    textEl: div.querySelector('.bubble-text'),
    metaEl: div.querySelector('.meta'),
    rawText: ''
  };
}

function appendBotText(shell, textChunk) {
  shell.rawText += textChunk;
  if (typeof window.marked !== 'undefined' && typeof window.marked.parse === 'function') {
    shell.textEl.innerHTML = window.marked.parse(shell.rawText);
  } else {
    shell.textEl.textContent = shell.rawText;
  }
  const box = document.getElementById('chatBox');
  box.scrollTop = box.scrollHeight;
}

function finalizeBotMessage(shell, data) {
  if (data.response) {
    shell.rawText = data.response;
  }
  if (typeof window.marked !== 'undefined' && typeof window.marked.parse === 'function') {
    shell.textEl.innerHTML = window.marked.parse(shell.rawText);
  } else {
    shell.textEl.textContent = shell.rawText;
  }

  const maskedBadge = data.was_masked
    ? `<span>🔒 <b>${data.masked_types.join(', ')}</b></span>`
    : '';

  const overrideBadge = data.routing_reason && data.routing_reason.includes('MANUAL')
    ? `<span>🎛️ <b>Override</b></span>`
    : '';

  const warningBadge = data.provider_reached === false
    ? `<span>⚠️ <b>Provider unreachable — $0 charged</b></span>`
    : '';

  const levelCap = data.complexity ? (data.complexity.charAt(0).toUpperCase() + data.complexity.slice(1)) : 'Simple';
  const latencyDisplay = data.latency_seconds || (data.latency_ms ? (data.latency_ms / 1000).toFixed(1) + 's' : '0s');
  const modelDisplay = data.provider_reached === false ? 'null' : (data.model_used || 'null');

  let pTok = 'N/A', cTok = 'N/A', tTok = 'N/A';
  if (data.provider_reached !== false && data.usage && typeof data.usage === 'object') {
    pTok = data.usage.prompt_tokens ?? 'N/A';
    cTok = data.usage.completion_tokens ?? 'N/A';
    tTok = data.usage.total_tokens ?? 'N/A';
  } else if (data.provider_reached === false) {
    pTok = 0; cTok = 0; tTok = 0;
  }

  const providerCost = typeof data.provider_cost === 'number' ? data.provider_cost.toFixed(4) : '0.0000';
  const estimatedCost = typeof data.estimated_cost === 'number' ? data.estimated_cost.toFixed(4) : '0.0010';
  const billedCost = typeof data.cost === 'number' ? data.cost.toFixed(4) : '0.0000';
  const budgetRem = typeof data.budget_remaining === 'number' ? Math.max(0, data.budget_remaining).toFixed(2) : '2.00';

  shell.metaEl.style.display = 'block';
  shell.metaEl.innerHTML = `
    <div class="meta-badge-row">
      <span>🧠 <b>${levelCap}</b> · ${data.complexity_score}/100</span>
      <span>⏱️ <b>${latencyDisplay}</b></span>
      <span>💰 <b>$${billedCost}</b></span>
      ${maskedBadge}
      ${overrideBadge}
      ${warningBadge}
    </div>
    <details class="meta-details">
      <summary class="meta-summary">▸ Response details</summary>
      <div class="details-grid">
        <div>🤖 <b>Model:</b> ${modelDisplay}</div>
        <div>📡 <b>Provider:</b> ${data.provider_used || 'openrouter'}</div>
        <div>🧠 <b>Complexity Tier:</b> ${levelCap}</div>
        <div>🎯 <b>Complexity Score:</b> ${data.complexity_score}/100</div>
        <div>⏱️ <b>Latency:</b> ${latencyDisplay}</div>
        <div>📥 <b>Prompt Tokens:</b> ${pTok}</div>
        <div>📤 <b>Completion Tokens:</b> ${cTok}</div>
        <div>🔤 <b>Total Tokens:</b> ${tTok}</div>
        <div>💰 <b>Provider Cost:</b> $${providerCost}</div>
        <div>💵 <b>Budget Remaining:</b> $${budgetRem}</div>
      </div>
    </details>
    <button class="tts-btn" onclick="playTTS(this)" title="Smallest AI Text-to-Speech">🔊 Listen</button>
  `;
  const box = document.getElementById('chatBox');
  box.scrollTop = box.scrollHeight;
}

function appendBlocked(data) {
  const box = document.getElementById('chatBox');
  const div = document.createElement('div');
  div.className = 'message blocked';
  div.innerHTML = `
    <div class="bubble">
      🚫 <b>BLOCKED</b><br>
      ⚠️ ${data.reason}<br>
      <div class="meta">Risk Score: ${data.risk_score}/100 | Action: ${data.action}</div>
    </div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function updateBudget(remaining) {
  const safeRem = Math.max(0, typeof remaining === 'number' ? remaining : 2.0);
  const pct = Math.min(100, Math.max(0, (safeRem / 2.0) * 100));
  const bar = document.getElementById('budgetBar');
  const text = document.getElementById('budgetText');
  if (bar) {
    bar.style.width = pct + '%';
    if (pct > 50) {
      bar.style.background = 'linear-gradient(90deg, #8B5CF6, #EC4899)';
    } else if (pct > 25) {
      bar.style.background = 'linear-gradient(90deg, #f59e0b, #ef4444)';
    } else {
      bar.style.background = '#ef4444';
    }
  }
  if (text) {
    text.textContent = `$${safeRem.toFixed(2)} remaining`;
  }
}

async function loadStats() {
  try {
    const res = await fetch(`${API}/stats`);
    const data = await res.json();
    document.getElementById('statSpent').textContent = `$${data.spent}`;
    document.getElementById('statRemaining').textContent = `$${data.remaining}`;
    document.getElementById('statRequests').textContent = data.requests;

    const log = document.getElementById('requestLog');
    log.innerHTML = '<h3 style="color:#666;margin-bottom:12px;font-size:13px;text-transform:uppercase;letter-spacing:1px">Request History</h3>';
    data.log.forEach((item, i) => {
      log.innerHTML += `
        <div class="log-item">
          <span style="color:#94a3b8">#${i+1} — ${item.prompt_preview}...</span>
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
      <div class="sim-value">$${cost} <span style="color:#4a5568;font-size:11px">(GPT-4 would cost $${gpt4cost})</span></div>
    </div>
    <div class="sim-step">
      <div class="sim-icon">📉</div>
      <div class="sim-label">Cost Saved</div>
      <div class="sim-value">${Math.round((1 - cost/gpt4cost)*100)}% cheaper than GPT-4</div>
    </div>
  `;
}

// ── THEME TOGGLE ──
function toggleTheme() {
  const body = document.body;
  const btn = document.getElementById('themeToggle');
  if (body.classList.contains('light')) {
    body.classList.remove('light');
    btn.textContent = '🌙 Dark Mode';
    localStorage.setItem('theme', 'dark');
  } else {
    body.classList.add('light');
    btn.textContent = '☀️ Light Mode';
    localStorage.setItem('theme', 'light');
  }
}

// ── INIT ──
updateBudget(2.0);

// Load saved theme & render logo rays
window.addEventListener('DOMContentLoaded', () => {
  renderLogoRays();
  if (localStorage.getItem('theme') === 'light') {
    document.body.classList.add('light');
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = '☀️ Light Mode';
  }
});

// ── SMALLEST AI VOICE INTEGRATION (STT & TTS) ──

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let currentAudio = null;

async function toggleRecording(targetInputId = 'userInput') {
  const input = document.getElementById(targetInputId) || document.getElementById('userInput');
  const micBtn = targetInputId === 'heroInput' ? document.getElementById('heroMicBtn') : document.getElementById('micBtn');
  const voiceStatus = document.getElementById('voiceStatus');

  if (isRecording) {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    isRecording = false;
    if (micBtn) {
      micBtn.classList.remove('recording');
      micBtn.innerHTML = '🎙️';
    }
    if (voiceStatus) {
      voiceStatus.style.display = 'flex';
      voiceStatus.innerHTML = '<span>⚡ Transcribing audio with Smallest AI (Pulse)...</span>';
    }
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        audioChunks.push(e.data);
      }
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(track => track.stop());
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

      try {
        const response = await fetch(`${API}/api/stt`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/octet-stream' },
          body: audioBlob
        });

        const data = await response.json();
        voiceStatus.style.display = 'none';

        if (data.transcription) {
          input.value = data.transcription;
          input.focus();
        } else if (data.error) {
          alert(`STT Error: ${data.error}`);
        }
      } catch (err) {
        voiceStatus.style.display = 'none';
        alert('Failed to connect to STT service.');
      }
    };

    mediaRecorder.start();
    isRecording = true;
    micBtn.classList.add('recording');
    micBtn.innerHTML = '⏹️';
    voiceStatus.style.display = 'flex';
    voiceStatus.innerHTML = '<span>🔴 Recording audio... Click mic again when finished</span>';
  } catch (err) {
    alert('Microphone access denied or unavailable: ' + err.message);
  }
}

async function playTTS(btn) {
  const bubble = btn.closest('.bubble');
  const textEl = bubble ? bubble.querySelector('.bubble-text') : null;
  const text = textEl ? textEl.textContent.trim() : '';

  if (!text) return;

  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  const originalHtml = btn.innerHTML;
  btn.innerHTML = '⏳ Loading audio...';
  btn.disabled = true;

  try {
    const response = await fetch(`${API}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, voice_id: 'meher' })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || 'TTS Request Failed');
    }

    const blob = await response.blob();
    const audioUrl = URL.createObjectURL(blob);
    currentAudio = new Audio(audioUrl);

    btn.innerHTML = '🔊 Playing...';
    btn.classList.add('playing');
    btn.disabled = false;

    currentAudio.onended = () => {
      btn.innerHTML = originalHtml;
      btn.classList.remove('playing');
      currentAudio = null;
    };

    await currentAudio.play();
  } catch (err) {
    alert('Smallest AI TTS Error: ' + err.message);
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    btn.classList.remove('playing');
  }
}