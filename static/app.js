/**
 * UNIchat - Frontend Application
 * Handles chat interactions, message rendering, and UI state.
 */

const API_URL = '/api/chat';

// DOM Elements
const chatArea = document.getElementById('chatArea');
const messagesEl = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const typingIndicator = document.getElementById('typingIndicator');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const suggestionChips = document.getElementById('suggestionChips');

let isProcessing = false;

// ──────────────────────────────────────────────
// Message Rendering
// ──────────────────────────────────────────────

function createBotAvatar() {
    return `<div class="msg-avatar">
        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="10" fill="url(#bg${Date.now()})"/>
            <path d="M10 22V12l6 5 6-5v10" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <defs>
                <linearGradient id="bg${Date.now()}" x1="0" y1="0" x2="32" y2="32">
                    <stop stop-color="#F59E0B"/>
                    <stop offset="1" stop-color="#EF4444"/>
                </linearGradient>
            </defs>
        </svg>
    </div>`;
}

function formatResponse(text) {
    // Convert markdown-like formatting to HTML
    let html = text
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Line breaks
        .replace(/\n/g, '<br>')
        // Bullet points
        .replace(/^- (.+)/gm, '&bull; $1')
        .replace(/<br>&bull;/g, '<br>&bull;');
    return html;
}

function addMessage(content, type) {
    // Hide welcome on first message
    if (welcome.style.display !== 'none') {
        welcome.style.display = 'none';
    }

    const msgEl = document.createElement('div');
    msgEl.className = `message ${type}`;

    if (type === 'user') {
        msgEl.innerHTML = `
            <div class="msg-avatar">U</div>
            <div class="msg-content">${escapeHtml(content)}</div>
        `;
    } else {
        msgEl.innerHTML = `
            ${createBotAvatar()}
            <div class="msg-content">${formatResponse(content)}</div>
        `;
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
    requestAnimationFrame(() => {
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

    // Show user message
    addMessage(text, 'user');

    // Show typing indicator
    showTyping();

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        });

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const data = await response.json();
        hideTyping();
        addMessage(data.response, 'bot');
    } catch (err) {
        hideTyping();
        console.error('Chat error:', err);
        addMessage(
            "Oops, something went wrong on my end. Try again in a sec, or reach out directly:\n\n" +
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

// Enter to send, Shift+Enter for newline
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(messageInput.value);
    }
});

messageInput.addEventListener('input', () => {
    updateSendButton();
    autoResizeInput();
});

sendBtn.addEventListener('click', () => {
    sendMessage(messageInput.value);
});

// Suggestion chips
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const query = chip.dataset.query;
        sendMessage(query);
    });
});

// Focus input on load
window.addEventListener('load', () => {
    messageInput.focus();
});
