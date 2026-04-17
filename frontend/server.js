/**
 * UNIchat Frontend Server
 * Express.js server serving the chat UI and proxying API calls to Python backend.
 */

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const API_URL = process.env.API_URL || 'http://127.0.0.1:8000';

// ── Proxy /api/* to Python backend ──
app.use(createProxyMiddleware({
    pathFilter: '/api',
    target: API_URL,
    changeOrigin: true,
    timeout: 30000,
    onError: (err, req, res) => {
        console.error('[Proxy] Backend error:', err.message);
        res.status(502).json({
            response: "The AI backend is starting up or unavailable. Try again in a moment.\n\n" +
                "If this persists, contact MUJ directly:\n" +
                "- Toll-free: 18001020128\n" +
                "- WhatsApp: +91 83062 48211\n" +
                "- Email: admissions@jaipur.manipal.edu",
            sources: [],
            backend: "error"
        });
    }
}));


// ── Serve static frontend files ──
app.use(express.static(path.join(__dirname, 'public')));

// ── SPA fallback ──
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ── Start ──
app.listen(PORT, () => {
    console.log('');
    console.log('╔══════════════════════════════════════════╗');
    console.log('║         UNIchat Frontend Server          ║');
    console.log('╠══════════════════════════════════════════╣');
    console.log(`║  URL:     http://localhost:${PORT}           ║`);
    console.log(`║  API:     ${API_URL}     ║`);
    console.log('║  Status:  Running                        ║');
    console.log('╚══════════════════════════════════════════╝');
    console.log('');
});
