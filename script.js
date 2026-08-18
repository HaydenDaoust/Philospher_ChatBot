/**
 * Aristotle Chatbot — Frontend Logic
 *
 * Flow:
 *  1. On page load: generate a session_id (UUID v4), show opening greeting.
 *  2. On submit: POST /chat, update UI, manage terminal states.
 *  3. Conversation history kept locally; sent with every request.
 */

'use strict';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const API_URL = '/chat';

const TONE_IMAGES = {
  neutral:      '/images/neutral.png',
  approving:    '/images/approving.png',
  skeptical:    '/images/skeptical.png',
  disappointed: '/images/disappointed.png',
  probing:      '/images/probing.png',
};

const TOPIC_LABELS = {
  eudaimonia:         'Eudaimonia',
  doctrine_of_mean:   'Doctrine of the Mean',
  habit_and_practice: 'Habit & Practice',
  phronesis:          'Phronesis',
};

const TOPIC_ORDER = ['eudaimonia', 'doctrine_of_mean', 'habit_and_practice', 'phronesis'];

// Opening message displayed before the first API call
const OPENING_MESSAGE =
  'Welcome, student. Sit, and let us reason together. ' +
  'I wish to speak with you today about eudaimonia — the highest good, ' +
  'the end toward which all human activity aims. ' +
  'Tell me: what do you suppose it is that every person, in everything they do, is ultimately seeking?';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const sessionId = generateUUID();
let conversationHistory = [];   // [{ role: 'assistant'|'user', content: string }]
let isTerminal = false;

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------

const chatHistory    = document.getElementById('chat-history');
const chatForm       = document.getElementById('chat-form');
const userInput      = document.getElementById('user-input');
const submitBtn      = document.getElementById('submit-btn');
const btnLabel       = document.getElementById('btn-label');
const btnSpinner     = document.getElementById('btn-spinner');
const typingIndicator= document.getElementById('typing-indicator');
const aristotleImg   = document.getElementById('aristotle-img');
const stateTopic     = document.getElementById('state-topic');
const stateStage     = document.getElementById('state-stage');
const stateTone      = document.getElementById('state-tone');
const terminalBanner = document.getElementById('terminal-banner');
const topicPips      = document.querySelectorAll('.topic-pip');

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

window.addEventListener('DOMContentLoaded', () => {
  appendMessage('aristotle', OPENING_MESSAGE);
  conversationHistory.push({ role: 'assistant', content: OPENING_MESSAGE });

  // Set initial state display
  updateStateDisplay({ topic: 'eudaimonia', stage: 'introduction', tone: 'neutral' });

  userInput.focus();
});

// ---------------------------------------------------------------------------
// Form submission
// ---------------------------------------------------------------------------

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (isTerminal) return;

  const text = userInput.value.trim();
  if (!text) return;

  // Show student message immediately
  appendMessage('student', text);
  conversationHistory.push({ role: 'user', content: text });
  userInput.value = '';

  // UI: loading state
  setLoading(true);

  try {
    const data = await postChat(text);
    handleResponse(data);
  } catch (err) {
    appendError(err.message || 'Could not reach the server. Is the backend running?');
  } finally {
    setLoading(false);
  }
});

// Submit on Enter (Shift+Enter for newline)
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
  }
});

// ---------------------------------------------------------------------------
// API call
// ---------------------------------------------------------------------------

async function postChat(userText) {
  const body = {
    session_id: sessionId,
    user_input: userText,
    conversation_history: conversationHistory.slice(0, -1), // exclude the message we just appended
  };

  const res = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Server error ${res.status}: ${errText}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Response handler
// ---------------------------------------------------------------------------

function handleResponse(data) {
  // Append Aristotle's reply
  appendMessage('aristotle', data.response);
  conversationHistory.push({ role: 'assistant', content: data.response });

  // Update portrait & state display
  updatePortrait(data.tone);
  updateStateDisplay(data);

  // Terminal handling
  if (data.is_terminal) {
    isTerminal = true;
    lockInput();
    showTerminalBanner(data.terminal_type);
  }
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function appendMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;

  const label = document.createElement('div');
  label.className = 'message-label';
  label.textContent = role === 'aristotle' ? 'Aristotle' : 'You';

  const body = document.createElement('div');
  body.className = 'message-body';
  body.textContent = text;   // textContent is XSS-safe

  wrapper.appendChild(label);
  wrapper.appendChild(body);
  chatHistory.appendChild(wrapper);
  scrollToBottom();
}

function appendError(msg) {
  const el = document.createElement('div');
  el.className = 'message aristotle';
  el.style.borderColor = '#c0392b';
  el.style.color = '#7b241c';

  const label = document.createElement('div');
  label.className = 'message-label';
  label.textContent = 'Error';

  const body = document.createElement('div');
  body.textContent = msg;

  el.appendChild(label);
  el.appendChild(body);
  chatHistory.appendChild(el);
  scrollToBottom();
}

function scrollToBottom() {
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function setLoading(loading) {
  submitBtn.disabled = loading;
  userInput.disabled = loading;
  btnLabel.classList.toggle('hidden', loading);
  btnSpinner.classList.toggle('hidden', !loading);
  typingIndicator.classList.toggle('hidden', !loading);
  if (loading) scrollToBottom();
}

function lockInput() {
  userInput.disabled = true;
  submitBtn.disabled = true;
  userInput.placeholder = 'This dialogue has concluded.';
}

function showTerminalBanner(terminalType) {
  terminalBanner.classList.remove('hidden', 'end', 'dismissed');
  if (terminalType === 'end') {
    terminalBanner.classList.add('end');
    terminalBanner.textContent =
      'The dialogue is complete. You have traversed all four pillars of virtue ethics.';
  } else {
    terminalBanner.classList.add('dismissed');
    terminalBanner.textContent =
      'You have been dismissed. Reflect on what was asked of you, and return when ready.';
  }
}

function updatePortrait(tone) {
  const src = TONE_IMAGES[tone] || TONE_IMAGES.neutral;
  if (aristotleImg.src !== src) {
    aristotleImg.style.opacity = '0';
    setTimeout(() => {
      aristotleImg.src = src;
      aristotleImg.style.opacity = '1';
    }, 180);
  }
  document.body.dataset.tone = tone || 'neutral';
}

function updateStateDisplay({ topic, stage, tone }) {
  if (topic) {
    stateTopic.textContent = TOPIC_LABELS[topic] || topic;
    updateTopicPips(topic);
  }
  if (stage) stateStage.textContent = formatLabel(stage);
  if (tone)  stateTone.textContent  = formatLabel(tone);
}

function updateTopicPips(currentTopic) {
  const currentIdx = TOPIC_ORDER.indexOf(currentTopic);
  topicPips.forEach((pip) => {
    const t = pip.dataset.topic;
    const idx = TOPIC_ORDER.indexOf(t);
    pip.classList.remove('active', 'done');
    if (idx < currentIdx)  pip.classList.add('done');
    if (idx === currentIdx) pip.classList.add('active');
  });
}

function formatLabel(str) {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// UUID v4 generator (no dependencies)
// ---------------------------------------------------------------------------

function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older environments
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
