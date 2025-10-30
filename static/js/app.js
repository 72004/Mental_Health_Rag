const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const chatText = document.getElementById('chat-text');
const sendBtn = document.getElementById('send-btn');
const errorBox = document.getElementById('error');

function appendMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '🧍‍♂️' : '🕊️';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = text
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function appendTyping() {
  const el = document.createElement('div');
  el.className = 'message assistant';
  el.id = 'typing';
  el.innerHTML = '<div class="avatar">🕊️</div><div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div>';
  chatWindow.appendChild(el);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typing');
  if (el) el.remove();
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = chatText.value.trim();
  if (!text) return;

  errorBox.hidden = true; errorBox.textContent = '';
  appendMessage('user', text);
  chatText.value = '';
  chatText.focus();
  sendBtn.disabled = true;
  appendTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    removeTyping();
    if (!res.ok) throw new Error(data.error || 'Something went wrong');
    appendMessage('assistant', data.reply || '');
  } catch (err) {
    removeTyping();
    errorBox.hidden = false;
    errorBox.textContent = err.message;
  } finally {
    sendBtn.disabled = false;
  }
});


