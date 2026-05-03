/* ElectoGuide AI — Frontend Application Logic */
'use strict';

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  persona: 'general',
  chatHistory: [],
  quizData: null,
  quizIndex: 0,
  quizScore: 0,
  quizAnswered: false,
  isSpeaking: false,
  ttsEnabled: true,
  highContrast: false,
  largeFont: false,
};

// ── Utility ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const qs = sel => document.querySelector(sel);
const qsa = sel => document.querySelectorAll(sel);

function showToast(msg, duration = 3000) {
  const t = $('toast');
  t.textContent = msg;
  t.style.display = 'block';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.style.display = 'none', duration);
}

function renderMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/^[-•] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, m => `<ul>${m}</ul>`)
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hublcp])(.+)$/gm, '<p>$1</p>')
    .replace(/<p><\/p>/g, '');
}

async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${r.status}`);
  }
  return r.json();
}

async function apiGet(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Navigation ────────────────────────────────────────────────────────────────
function navigateTo(pageId) {
  qsa('.page').forEach(p => p.classList.remove('active'));
  qsa('.nav-link').forEach(l => l.classList.remove('active'));
  const page = $(pageId);
  if (page) page.classList.add('active');
  const link = qs(`[data-page="${pageId}"]`);
  if (link) link.classList.add('active');
  window.scrollTo(0, 0);

  // Lazy load page data
  if (pageId === 'page-countries') loadCountriesList();
  if (pageId === 'page-factcheck') loadFactcheckExamples();
  if (pageId === 'page-journey') loadJourneyCountries();
}

// ── Hero / Persona ────────────────────────────────────────────────────────────
function initHero() {
  qsa('.persona-card').forEach(card => {
    card.addEventListener('click', () => {
      qsa('.persona-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      state.persona = card.dataset.persona;
      qsa('.persona-pill').forEach(p => {
        p.classList.toggle('active', p.dataset.persona === state.persona);
      });
      showToast(`Persona set: ${card.querySelector('h4').textContent}`);
    });
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        card.click();
      }
    });
  });

  $('hero-start-btn').addEventListener('click', () => {
    navigateTo('page-chat');
  });
  $('hero-explore-btn').addEventListener('click', () => {
    navigateTo('page-countries');
  });
}

// ── Chat ──────────────────────────────────────────────────────────────────────
const QUICK_QUESTIONS = [
  { icon: '🗳️', title: 'How do I register to vote?', sub: 'Registration steps' },
  { icon: '📅', title: 'What are key election dates?', sub: 'Timelines & deadlines' },
  { icon: '🏛️', title: 'How does the Electoral College work?', sub: 'US election system' },
  { icon: '📬', title: 'Can I vote by mail?', sub: 'Absentee & mail-in' },
  { icon: '🌍', title: 'Compare election systems', sub: 'First Past the Post vs PR' },
  { icon: '🆔', title: 'What ID do I need to vote?', sub: 'Documentation guide' },
];

function buildChatPage() {
  // Quick action cards
  const grid = $('quick-actions');
  QUICK_QUESTIONS.forEach(q => {
    const card = document.createElement('div');
    card.className = 'quick-card';
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.innerHTML = `<div class="qicon">${q.icon}</div><div class="qtext"><h5>${q.title}</h5><p>${q.sub}</p></div>`;
    card.addEventListener('click', () => sendChatMessage(q.title));
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); }
    });
    grid.appendChild(card);
  });

  // Persona pills
  const pills = $('persona-pills');
  const personas = [
    { id: 'general', label: '👤 General' },
    { id: 'student', label: '📚 Student' },
    { id: 'first_voter', label: '🗳️ First Voter' },
    { id: 'researcher', label: '🔬 Researcher' },
    { id: 'senior', label: '🧓 Senior' },
  ];
  personas.forEach(p => {
    const pill = document.createElement('button');
    pill.className = 'persona-pill' + (p.id === state.persona ? ' active' : '');
    pill.dataset.persona = p.id;
    pill.textContent = p.label;
    pill.addEventListener('click', () => {
      state.persona = p.id;
      qsa('.persona-pill').forEach(x => x.classList.toggle('active', x.dataset.persona === p.id));
      showToast(`Persona: ${p.label}`);
    });
    pills.appendChild(pill);
  });
}

function appendMessage(role, html, rawText = '') {
  const msgs = $('chat-messages');
  const div = document.createElement('div');
  div.className = `msg ${role === 'user' ? 'user' : 'ai'}`;
  const avatar = role === 'user' ? '👤' : '🗳️';
  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div>
      <div class="msg-bubble">${html}</div>
      ${role !== 'user' ? `
        <div class="msg-actions">
          <button class="msg-action-btn" onclick="speakText(this)" data-text="${encodeURIComponent(rawText)}">🔊 Listen</button>
          <button class="msg-action-btn" onclick="copyText(this)" data-text="${encodeURIComponent(rawText)}">📋 Copy</button>
        </div>` : ''}
    </div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function showTypingIndicator() {
  const msgs = $('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg ai'; div.id = 'typing-indicator';
  div.innerHTML = `<div class="msg-avatar">🗳️</div>
    <div class="msg-bubble"><div class="typing-indicator">
      <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
    </div></div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeTypingIndicator() {
  const el = $('typing-indicator');
  if (el) el.remove();
}

async function sendChatMessage(text) {
  if (!text || !text.trim()) return;
  const input = $('chat-input');
  const btn = $('chat-send');
  const msg = text.trim();

  appendMessage('user', renderMarkdown(msg), msg);
  state.chatHistory.push({ role: 'user', content: msg });
  input.value = '';
  btn.disabled = true;
  showTypingIndicator();

  // Hide quick actions after first message
  const qa = $('quick-actions');
  if (qa) qa.style.display = 'none';

  try {
    const data = await apiPost('/api/chat', {
      message: msg,
      history: state.chatHistory.slice(-10),
      persona: state.persona,
    });
    removeTypingIndicator();
    const html = renderMarkdown(data.response);
    appendMessage('ai', html, data.response);
    state.chatHistory.push({ role: 'model', content: data.response });
  } catch (err) {
    removeTypingIndicator();
    appendMessage('ai', `<span style="color:var(--danger)">⚠️ ${err.message}. Please try again.</span>`, '');
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

function initChat() {
  buildChatPage();
  const input = $('chat-input');
  const btn = $('chat-send');

  btn.addEventListener('click', () => sendChatMessage(input.value));
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(input.value); }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
}

// ── TTS ───────────────────────────────────────────────────────────────────────
let currentAudio = null;

async function speakText(btn) {
  let text = decodeURIComponent(btn.dataset.text);
  if (!text) return;

  if (state.isSpeaking) { 
    speechSynthesis.cancel(); 
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }
    state.isSpeaking = false; 
    btn.textContent = '🔊 Listen'; 
    return; 
  }

  // Clean markdown and emojis for TTS
  text = text.replace(/\*\*/g, '')
             .replace(/\*/g, '')
             .replace(/#/g, '')
             .replace(/`/g, '')
             .replace(/\[(.*?)\]\(.*?\)/g, '$1')
             .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
             .trim();

  try {
    // Try server TTS first; fall back to browser
    const data = await apiPost('/api/tts', { text: text.slice(0, 4000) });
    if (!data.use_browser_tts && data.audio_base64) {
      currentAudio = new Audio(`data:audio/mp3;base64,${data.audio_base64}`);
      state.isSpeaking = true;
      btn.textContent = '⏹ Stop';
      currentAudio.onended = () => { state.isSpeaking = false; btn.textContent = '🔊 Listen'; currentAudio = null; };
      currentAudio.play();
    } else {
      useBrowserTTS(text, btn);
    }
  } catch {
    useBrowserTTS(text, btn);
  }
}

function useBrowserTTS(text, btn) {
  if (!window.speechSynthesis) { showToast('TTS not supported in this browser'); return; }
  speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.rate = 0.95; utt.pitch = 1;
  state.isSpeaking = true;
  if (btn) btn.textContent = '⏹ Stop';
  utt.onend = () => { state.isSpeaking = false; if (btn) btn.textContent = '🔊 Listen'; };
  speechSynthesis.speak(utt);
}

function copyText(btn) {
  const text = decodeURIComponent(btn.dataset.text);
  navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard!'));
}

// ── Countries ─────────────────────────────────────────────────────────────────
async function loadCountriesList() {
  const grid = $('countries-grid');
  if (grid.dataset.loaded) return;
  grid.dataset.loaded = '1';
  grid.innerHTML = '<div class="spinner" style="margin:40px auto"></div>';
  try {
    const data = await apiGet('/api/countries');
    grid.innerHTML = '';
    data.countries.forEach(c => {
      const card = document.createElement('div');
      card.className = 'country-card';
      card.tabIndex = 0;
      card.setAttribute('role', 'button');
      card.innerHTML = `<div class="flag">${c.emoji}</div><h4>${c.name}</h4><p>${c.system}</p>`;
      card.addEventListener('click', () => openCountryModal(c.name, c.emoji));
      card.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); }
      });
      grid.appendChild(card);
    });
  } catch (e) {
    grid.innerHTML = `<p style="color:var(--danger)">${e.message}</p>`;
  }
}

async function openCountryModal(name, emoji) {
  const modal = $('country-modal');
  const content = $('modal-content');
  modal.classList.add('open');
  content.innerHTML = '<div class="spinner" style="margin:60px auto"></div>';

  try {
    const d = await apiGet(`/api/countries/${encodeURIComponent(name)}`);
    content.innerHTML = `
      <button class="modal-close" onclick="closeCountryModal()">✕</button>
      <h2 style="font-family:'Space Grotesk',sans-serif;font-size:24px;margin-bottom:4px">${emoji} ${d.country}</h2>
      <p style="color:var(--text-secondary);margin-bottom:20px">${d.system_type} · ${d.electoral_system}</p>
      <div class="info-tags">
        <span class="info-tag">🗳️ Voting age: <strong>${d.voting_age}</strong></span>
        <span class="info-tag">📅 Every <strong>${d.election_frequency_years} years</strong></span>
        <span class="info-tag">📋 Registration: <strong>${d.registration_required ? 'Required' : 'Automatic'}</strong></span>
        <span class="info-tag">⚖️ Compulsory: <strong>${d.compulsory_voting ? 'Yes' : 'No'}</strong></span>
      </div>
      <h3 class="section-title" style="font-size:18px;margin-top:24px">Election Timeline</h3>
      <div class="timeline-steps">${(d.timeline||[]).map((t,i)=>`
        <div class="timeline-step">
          <div class="step-number">${i+1}</div>
          <div class="step-content"><h5>${t.phase} <span style="color:var(--accent2);font-size:12px">${t.timing}</span></h5><p>${t.description}</p></div>
        </div>`).join('')}</div>
      <h3 class="section-title" style="font-size:18px;margin-top:24px">Key Steps for Voters</h3>
      <ol style="padding-left:20px;color:var(--text-secondary);line-height:2">${(d.key_steps||[]).map(s=>`<li>${s}</li>`).join('')}</ol>
      ${d.unique_features?.length ? `<h3 class="section-title" style="font-size:18px;margin-top:24px">Unique Features</h3>
      <ul style="padding-left:20px;color:var(--text-secondary);line-height:2">${d.unique_features.map(f=>`<li>${f}</li>`).join('')}</ul>` : ''}
      <div style="margin-top:20px;padding:16px;border-radius:10px;background:rgba(246,224,94,0.08);border:1px solid rgba(246,224,94,0.2)">
        💡 <strong>Fun fact:</strong> <span style="color:var(--text-secondary)">${d.fun_fact}</span>
      </div>
      <button class="btn btn-primary" style="margin-top:20px" onclick="askAboutCountry('${name}')">💬 Ask ElectoGuide AI about ${name}</button>`;
  } catch (e) {
    content.innerHTML = `<button class="modal-close" onclick="closeCountryModal()">✕</button><p style="color:var(--danger)">Error: ${e.message}</p>`;
  }
}

function closeCountryModal() { $('country-modal').classList.remove('open'); }
function askAboutCountry(name) {
  closeCountryModal();
  navigateTo('page-chat');
  setTimeout(() => sendChatMessage(`Tell me about the election process in ${name}`), 300);
}

// ── Quiz ──────────────────────────────────────────────────────────────────────
async function startQuiz(topic, difficulty) {
  $('quiz-start').style.display = 'none';
  $('quiz-loading').style.display = 'block';
  $('quiz-game').style.display = 'none';
  $('quiz-result').style.display = 'none';

  try {
    const data = await apiPost('/api/quiz', { topic, difficulty, count: 5 });
    state.quizData = data.questions;
    state.quizIndex = 0;
    state.quizScore = 0;
    $('quiz-loading').style.display = 'none';
    $('quiz-game').style.display = 'block';
    renderQuestion();
  } catch (e) {
    $('quiz-loading').style.display = 'none';
    $('quiz-start').style.display = 'block';
    showToast(`Error: ${e.message}`, 4000);
  }
}

function renderQuestion() {
  const q = state.quizData[state.quizIndex];
  const total = state.quizData.length;
  const pct = (state.quizIndex / total) * 100;
  $('quiz-progress-fill').style.width = pct + '%';
  $('quiz-q-num').textContent = `Question ${state.quizIndex + 1} of ${total}`;
  $('quiz-question').textContent = q.question;

  const opts = $('quiz-options');
  opts.innerHTML = '';
  state.quizAnswered = false;

  q.options.forEach((opt, i) => {
    const btn = document.createElement('button');
    btn.className = 'quiz-option'; btn.textContent = opt;
    btn.addEventListener('click', () => answerQuestion(i));
    opts.appendChild(btn);
  });
  $('quiz-explanation').style.display = 'none';
  $('quiz-next-btn').style.display = 'none';
}

function answerQuestion(idx) {
  if (state.quizAnswered) return;
  state.quizAnswered = true;
  const q = state.quizData[state.quizIndex];
  const btns = qsa('.quiz-option');

  btns.forEach((btn, i) => {
    btn.disabled = true;
    if (i === q.correct) btn.classList.add('correct');
    else if (i === idx) btn.classList.add('wrong');
  });

  if (idx === q.correct) state.quizScore++;

  const exp = $('quiz-explanation');
  exp.innerHTML = `${idx === q.correct ? '✅ Correct!' : '❌ Incorrect.'} ${q.explanation}`;
  exp.style.display = 'block';
  $('quiz-next-btn').style.display = 'block';
}

function nextQuestion() {
  state.quizIndex++;
  if (state.quizIndex >= state.quizData.length) {
    showQuizResult();
  } else {
    renderQuestion();
  }
}

function showQuizResult() {
  $('quiz-game').style.display = 'none';
  const result = $('quiz-result');
  result.style.display = 'block';
  const pct = Math.round((state.quizScore / state.quizData.length) * 100);
  const ring = $('score-ring');
  ring.style.setProperty('--pct', pct + '%');
  $('score-text').textContent = `${state.quizScore}/${state.quizData.length}`;
  const msgs = ['Great start! Keep learning! 📚', 'Good effort! Review the material! 👍', 'Well done! You know your civics! 🎉', 'Excellent! You\'re an election expert! 🏆'];
  $('score-msg').textContent = msgs[Math.min(Math.floor(pct / 30), 3)];
}

// ── Fact Check ────────────────────────────────────────────────────────────────
async function loadFactcheckExamples() {
  const container = $('myth-examples');
  if (container.dataset.loaded) return;
  container.dataset.loaded = '1';
  try {
    const data = await apiGet('/api/factcheck/examples');
    container.innerHTML = '';
    data.examples.forEach(ex => {
      const chip = document.createElement('button');
      chip.className = 'myth-chip'; chip.textContent = ex;
      chip.addEventListener('click', () => { $('factcheck-input').value = ex; });
      container.appendChild(chip);
    });
  } catch {}
}

async function runFactCheck() {
  const claim = $('factcheck-input').value.trim();
  if (!claim || claim.length < 10) { showToast('Please enter a longer claim to check'); return; }

  const btn = $('factcheck-btn');
  const result = $('factcheck-result');
  btn.disabled = true;
  btn.textContent = 'Checking…';
  result.innerHTML = '<div class="spinner" style="margin:30px auto"></div>';

  try {
    const d = await apiPost('/api/factcheck', { claim });
    const verdictClass = {
      'TRUE': 'true', 'FALSE': 'false',
      'PARTIALLY TRUE': 'partial', 'MISLEADING': 'partial',
      'UNVERIFIABLE': 'unverifiable'
    }[d.verdict] || 'unverifiable';

    result.innerHTML = `
      <div class="verdict-card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
          <span class="badge badge-${verdictClass}">${d.verdict}</span>
          <span style="font-size:12px;color:var(--text-secondary)">Confidence: ${d.confidence}%</span>
        </div>
        <p style="font-style:italic;color:var(--text-secondary);margin-bottom:12px">"${d.claim}"</p>
        <p style="margin-bottom:12px">${d.explanation}</p>
        ${d.context ? `<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">${d.context}</p>` : ''}
        <div class="confidence-bar"><div class="confidence-fill" style="width:${d.confidence}%"></div></div>
        ${d.sources_hint ? `<p style="margin-top:12px;font-size:13px;color:var(--text-muted)">📚 Sources to check: ${d.sources_hint}</p>` : ''}
        <button class="btn btn-ghost" style="margin-top:16px" onclick="askAboutFactCheck('${encodeURIComponent(claim)}')">💬 Discuss with AI</button>
      </div>`;
  } catch (e) {
    result.innerHTML = `<p style="color:var(--danger)">Error: ${e.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 Check this Claim';
  }
}

function askAboutFactCheck(encodedClaim) {
  navigateTo('page-chat');
  setTimeout(() => sendChatMessage(`Can you explain more about this election claim: ${decodeURIComponent(encodedClaim)}`), 300);
}

// ── Voter Journey ─────────────────────────────────────────────────────────────
async function loadJourneyCountries() {
  const grid = $('journey-country-grid');
  if (grid.dataset.loaded) return;
  grid.dataset.loaded = '1';
  try {
    const data = await apiGet('/api/countries');
    grid.innerHTML = '';
    data.countries.slice(0, 8).forEach(c => {
      const btn = document.createElement('button');
      btn.className = 'journey-country-btn';
      btn.innerHTML = `<span class="flag">${c.emoji}</span><span>${c.name}</span>`;
      btn.addEventListener('click', () => loadJourney(c.name));
      grid.appendChild(btn);
    });
  } catch {}
}

async function loadJourney(country) {
  qsa('.journey-country-btn').forEach(b => b.classList.toggle('active', b.querySelector('span:last-child').textContent === country));
  const container = $('journey-steps');
  container.innerHTML = '<div class="spinner" style="margin:40px auto"></div>';

  try {
    const d = await apiGet(`/api/countries/${encodeURIComponent(country)}/journey?persona=${state.persona}`);
    container.innerHTML = `
      <h3 style="font-family:'Space Grotesk',sans-serif;font-size:20px;margin-bottom:24px">${d.journey_title}</h3>
      ${(d.steps||[]).map(s => `
        <div class="journey-step">
          <div class="journey-icon">${s.icon || '✅'}</div>
          <div class="journey-content">
            <h4>${s.title}</h4>
            <p>${s.description}</p>
            ${s.deadline_note ? `<span class="deadline-note">⏰ ${s.deadline_note}</span>` : ''}
            ${s.tips?.length ? `<ul style="margin-top:10px;padding-left:18px;font-size:13px;color:var(--text-secondary)">${s.tips.map(t=>`<li>${t}</li>`).join('')}</ul>` : ''}
            ${s.official_resource ? `<p style="margin-top:8px;font-size:12px;color:var(--text-muted)">📎 ${s.official_resource}</p>` : ''}
          </div>
        </div>`).join('')}
      ${d.accessibility_note ? `<div style="margin-top:20px;padding:16px;border-radius:10px;background:rgba(99,179,237,0.06);border:1px solid rgba(99,179,237,0.2)">
        ♿ <strong>Accessibility:</strong> <span style="color:var(--text-secondary)">${d.accessibility_note}</span></div>` : ''}`;
  } catch (e) {
    container.innerHTML = `<p style="color:var(--danger)">Error: ${e.message}</p>`;
  }
}

// ── Accessibility Controls ────────────────────────────────────────────────────
function initA11y() {
  $('a11y-tts').addEventListener('click', () => {
    state.ttsEnabled = !state.ttsEnabled;
    $('a11y-tts').classList.toggle('active', state.ttsEnabled);
    showToast(state.ttsEnabled ? 'Voice enabled' : 'Voice disabled');
  });
  $('a11y-contrast').addEventListener('click', () => {
    state.highContrast = !state.highContrast;
    document.body.classList.toggle('high-contrast', state.highContrast);
    $('a11y-contrast').classList.toggle('active', state.highContrast);
  });
  $('a11y-font').addEventListener('click', () => {
    state.largeFont = !state.largeFont;
    document.body.classList.toggle('large-font', state.largeFont);
    $('a11y-font').classList.toggle('active', state.largeFont);
  });
  $('a11y-stop').addEventListener('click', () => {
    speechSynthesis.cancel();
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }
    state.isSpeaking = false;
    // Reset all listen buttons
    qsa('.msg-action-btn').forEach(btn => {
      if (btn.textContent.includes('Stop')) btn.textContent = '🔊 Listen';
    });
    showToast('Speech stopped');
  });
}

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Nav links
  qsa('.nav-link[data-page]').forEach(link => {
    link.addEventListener('click', () => navigateTo(link.dataset.page));
  });

  // Hero buttons
  initHero();
  initChat();
  initA11y();

  // Quiz controls
  qsa('[data-quiz-topic]').forEach(btn => {
    btn.addEventListener('click', () => {
      const topic = btn.dataset.quizTopic;
      const diff = $('quiz-difficulty')?.value || 'medium';
      startQuiz(topic, diff);
    });
  });

  $('quiz-next-btn')?.addEventListener('click', nextQuestion);
  $('quiz-restart-btn')?.addEventListener('click', () => {
    $('quiz-result').style.display = 'none';
    $('quiz-start').style.display = 'block';
  });

  // Factcheck
  $('factcheck-btn')?.addEventListener('click', runFactCheck);
  $('factcheck-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') runFactCheck();
  });

  // Country modal close on backdrop
  $('country-modal')?.addEventListener('click', e => {
    if (e.target === $('country-modal')) closeCountryModal();
  });

  // Default page
  navigateTo('page-home');
});
