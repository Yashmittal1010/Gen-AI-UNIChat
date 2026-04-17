/**
 * UNIchat - Frontend Application
 * Handles chat interactions, session management, and message rendering.
 */

const API_URL = '/api/chat';
let sessionId = null;
let isProcessing = false;

// DOM
const chatArea = document.getElementById('chatArea');
const messagesEl = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const typingIndicator = document.getElementById('typingIndicator');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

// ──────────────────────────────────────────────
// Message Rendering
// ──────────────────────────────────────────────

function createBotAvatar() {
    const id = 'bg' + Math.random().toString(36).slice(2, 8);
    return '<div class="msg-avatar">' +
        '<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">' +
        '<rect width="32" height="32" rx="10" fill="url(#' + id + ')"/>' +
        '<path d="M10 22V12l6 5 6-5v10" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' +
        '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="32" y2="32">' +
        '<stop stop-color="#F59E0B"/><stop offset="1" stop-color="#EF4444"/>' +
        '</linearGradient></defs></svg></div>';
}

function formatResponse(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/^- (.+)/gm, '&bull; $1')
        .replace(/<br>&bull;/g, '<br>&bull;');
}

function addMessage(content, type) {
    if (welcome.style.display !== 'none') {
        welcome.style.display = 'none';
    }

    const msgEl = document.createElement('div');
    msgEl.className = 'message ' + type;

    if (type === 'user') {
        msgEl.innerHTML = '<div class="msg-avatar">U</div>' +
            '<div class="msg-content">' + escapeHtml(content) + '</div>';
    } else {
        msgEl.innerHTML = createBotAvatar() +
            '<div class="msg-content">' + formatResponse(content) + '</div>';
    }

    messagesEl.appendChild(msgEl);
    scrollToBottom();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    requestAnimationFrame(function() {
        chatArea.scrollTop = chatArea.scrollHeight;
    });
}

// ──────────────────────────────────────────────
// Typing Indicator
// ──────────────────────────────────────────────

function showTyping() {
    typingIndicator.classList.add('visible');
    scrollToBottom();
}

function hideTyping() {
    typingIndicator.classList.remove('visible');
}

// ──────────────────────────────────────────────
// Chat API
// ──────────────────────────────────────────────

async function sendMessage(text) {
    if (!text.trim() || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;
    messageInput.value = '';
    autoResizeInput();

    addMessage(text, 'user');
    showTyping();

    try {
        const body = { message: text };
        if (sessionId) body.session_id = sessionId;

        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) throw new Error('Server error: ' + response.status);

        const data = await response.json();
        hideTyping();

        // Store session ID from backend
        if (data.session_id) sessionId = data.session_id;

        addMessage(data.response, 'bot');
    } catch (err) {
        hideTyping();
        console.error('Chat error:', err);
        addMessage(
            "Oops, something went wrong. The backend might still be starting up - try again in a few seconds.\n\n" +
            "Or reach out directly:\n" +
            "- Toll-free: 18001020128\n" +
            "- WhatsApp: +91 83062 48211\n" +
            "- Email: admissions@jaipur.manipal.edu",
            'bot'
        );
    } finally {
        isProcessing = false;
        updateSendButton();
    }
}

// ──────────────────────────────────────────────
// Input Handling
// ──────────────────────────────────────────────

function updateSendButton() {
    sendBtn.disabled = !messageInput.value.trim() || isProcessing;
}

function autoResizeInput() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
}

messageInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(messageInput.value);
    }
});

messageInput.addEventListener('input', function() {
    updateSendButton();
    autoResizeInput();
});

sendBtn.addEventListener('click', function() {
    sendMessage(messageInput.value);
});

document.querySelectorAll('.chip').forEach(function(chip) {
    chip.addEventListener('click', function() {
        sendMessage(chip.dataset.query);
    });
});

window.addEventListener('load', function() {
    messageInput.focus();
});
