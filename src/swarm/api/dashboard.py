"""Chat-style interactive dashboard for Claude Swarm."""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Swarm</title>
<style>
  :root {
    --bg-primary: #0a0c10;
    --bg-secondary: #0d1117;
    --bg-tertiary: #161b22;
    --bg-input: #1c2128;
    --border: #21262d;
    --border-light: #30363d;
    --text-primary: #e6edf3;
    --text-secondary: #c9d1d9;
    --text-muted: #7d8590;
    --text-faint: #484f58;
    --accent: #58a6ff;
    --accent-dim: #1f6feb;
    --green: #3fb950;
    --green-dim: #0d4429;
    --yellow: #d29922;
    --yellow-dim: #3d2e00;
    --red: #f85149;
    --red-dim: #3d1a1a;
    --purple: #bc8cff;
    --purple-dim: #2d1b69;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text-secondary);
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* ---- Top bar ---- */
  .topbar {
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border);
    padding: 8px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 48px;
    flex-shrink: 0;
  }
  .topbar .logo { font-size: 16px; font-weight: 700; color: var(--text-primary); white-space: nowrap; }
  .topbar .logo span { color: var(--accent); }
  .topbar-badges { display: flex; gap: 6px; align-items: center; }
  .badge { padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; }
  .badge.online { background: var(--green-dim); color: var(--green); border: 1px solid #238636; }
  .badge.offline { background: var(--red-dim); color: var(--red); border: 1px solid #da3633; }
  .badge.backend { background: var(--purple-dim); color: var(--purple); border: 1px solid #6e40c9; }
  .topbar-stats { display: flex; gap: 16px; margin-left: auto; align-items: center; }
  .topbar-stat { font-size: 11px; color: var(--text-muted); }
  .topbar-stat strong { color: var(--text-primary); font-size: 13px; }
  .sidebar-toggle {
    background: none; border: 1px solid var(--border-light); color: var(--text-muted);
    width: 32px; height: 32px; border-radius: 6px; cursor: pointer; display: flex;
    align-items: center; justify-content: center; font-size: 16px; transition: all 0.15s;
  }
  .sidebar-toggle:hover { background: var(--bg-input); color: var(--text-primary); }

  /* ---- Main layout ---- */
  .main-layout {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* ---- Sidebar ---- */
  .sidebar {
    width: 320px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: width 0.2s ease, opacity 0.2s ease;
    flex-shrink: 0;
  }
  .sidebar.collapsed { width: 0; opacity: 0; pointer-events: none; }
  .sidebar-section { padding: 12px; border-bottom: 1px solid var(--border); }
  .sidebar-section h3 {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px;
    color: var(--text-muted); margin-bottom: 8px; display: flex; align-items: center; gap: 6px;
  }
  .sidebar-section h3 .count {
    background: var(--border); padding: 0 6px; border-radius: 8px; font-size: 10px;
  }

  /* Instance cards */
  .instance-card {
    background: var(--bg-tertiary); border: 1px solid var(--border);
    border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; font-size: 12px;
  }
  .instance-card .row { display: flex; justify-content: space-between; align-items: center; }
  .instance-card .id { font-family: 'Cascadia Code', monospace; color: var(--text-muted); font-size: 11px; }
  .pill { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 10px; font-weight: 600; }
  .pill.idle { background: var(--green-dim); color: var(--green); }
  .pill.busy { background: var(--yellow-dim); color: var(--yellow); }
  .pill.error { background: var(--red-dim); color: var(--red); }
  .pill.running { background: #1a2744; color: var(--accent); }
  .pill.completed { background: var(--green-dim); color: var(--green); }
  .pill.failed { background: var(--red-dim); color: var(--red); }
  .pill.queued, .pill.pending { background: var(--border); color: var(--text-muted); }
  .instance-card .task-label { color: var(--text-faint); margin-top: 4px; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .instance-card .stat-row { display: flex; gap: 10px; margin-top: 4px; }
  .instance-card .mini-stat { font-size: 10px; color: var(--text-faint); }
  .instance-card .mini-stat strong { color: var(--text-muted); }

  /* Activity feed */
  .activity-feed { flex: 1; overflow-y: auto; padding: 12px; }
  .activity-item {
    display: flex; gap: 8px; align-items: flex-start; margin-bottom: 8px;
    font-size: 12px; color: var(--text-muted);
  }
  .activity-dot {
    width: 6px; height: 6px; border-radius: 50%; margin-top: 5px; flex-shrink: 0;
  }
  .activity-dot.completed { background: var(--green); }
  .activity-dot.running { background: var(--accent); }
  .activity-dot.failed { background: var(--red); }
  .activity-dot.queued { background: var(--text-faint); }
  .activity-time { color: var(--text-faint); font-size: 10px; font-family: monospace; white-space: nowrap; }

  /* ---- Chat area ---- */
  .chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 0;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    scroll-behavior: smooth;
  }

  .message {
    max-width: 900px;
    margin: 0 auto 20px;
    display: flex;
    gap: 12px;
    animation: fadeIn 0.25s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

  .message .avatar {
    width: 32px; height: 32px; border-radius: 50%; display: flex;
    align-items: center; justify-content: center; font-size: 14px;
    flex-shrink: 0; font-weight: 700;
  }
  .message.user .avatar { background: var(--accent-dim); color: var(--accent); }
  .message.assistant .avatar { background: var(--purple-dim); color: var(--purple); }
  .message.system .avatar { background: var(--border); color: var(--text-muted); font-size: 12px; }

  .message .content { flex: 1; min-width: 0; }
  .message .sender {
    font-size: 12px; font-weight: 600; margin-bottom: 4px;
  }
  .message.user .sender { color: var(--accent); }
  .message.assistant .sender { color: var(--purple); }
  .message.system .sender { color: var(--text-muted); }

  .message .body {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-secondary);
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  .message.user .body { background: var(--accent-dim); border-color: #1a4a8a; }
  .message.system .body { background: var(--bg-secondary); border-style: dashed; }

  /* Markdown content styling */
  .message .body h1, .message .body h2, .message .body h3 {
    color: var(--text-primary); margin: 12px 0 6px; font-size: 15px;
  }
  .message .body h1 { font-size: 17px; }
  .message .body h2 { font-size: 16px; }
  .message .body p { margin: 6px 0; }
  .message .body ul, .message .body ol { margin: 6px 0 6px 20px; }
  .message .body li { margin: 2px 0; }
  .message .body code {
    background: var(--bg-primary); padding: 1px 5px; border-radius: 4px;
    font-family: 'Cascadia Code', 'JetBrains Mono', monospace; font-size: 13px;
    color: var(--accent);
  }
  .message .body pre {
    background: var(--bg-primary); border: 1px solid var(--border); border-radius: 6px;
    padding: 12px; margin: 8px 0; overflow-x: auto; font-size: 13px; line-height: 1.5;
  }
  .message .body pre code {
    background: none; padding: 0; color: var(--text-secondary); display: block;
  }
  .message .body blockquote {
    border-left: 3px solid var(--accent-dim); padding-left: 12px;
    color: var(--text-muted); margin: 8px 0;
  }
  .message .body strong { color: var(--text-primary); }
  .message .body a { color: var(--accent); text-decoration: none; }
  .message .body a:hover { text-decoration: underline; }
  .message .body table { border-collapse: collapse; margin: 8px 0; width: 100%; }
  .message .body th, .message .body td {
    border: 1px solid var(--border); padding: 6px 10px; font-size: 13px; text-align: left;
  }
  .message .body th { background: var(--bg-secondary); color: var(--text-primary); }

  /* Tool call blocks */
  .tool-calls { margin-top: 10px; }
  .tool-call {
    background: var(--bg-primary); border: 1px solid var(--border); border-radius: 6px;
    margin-bottom: 4px; font-size: 12px; overflow: hidden;
  }
  .tool-call-header {
    padding: 6px 10px; cursor: pointer; display: flex; align-items: center; gap: 6px;
    color: var(--text-muted); transition: background 0.15s;
  }
  .tool-call-header:hover { background: var(--bg-tertiary); }
  .tool-call-header .tool-icon { color: var(--accent); font-family: monospace; font-weight: 700; }
  .tool-call-header .tool-name { color: var(--text-secondary); font-family: monospace; }
  .tool-call-header .tool-dur { margin-left: auto; color: var(--text-faint); font-size: 10px; }
  .tool-call-header .tool-status { font-size: 10px; }
  .tool-call-header .tool-status.ok { color: var(--green); }
  .tool-call-header .tool-status.err { color: var(--red); }
  .tool-call-body {
    display: none; padding: 8px 10px; border-top: 1px solid var(--border);
    font-family: monospace; font-size: 11px; color: var(--text-faint);
    max-height: 200px; overflow-y: auto; white-space: pre-wrap;
  }
  .tool-call.expanded .tool-call-body { display: block; }
  .tool-arrow { font-size: 8px; transition: transform 0.15s; }
  .tool-call.expanded .tool-arrow { transform: rotate(90deg); }

  /* Task status badge in messages */
  .task-badge {
    display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
    border-radius: 6px; font-size: 11px; font-weight: 600; margin-bottom: 8px;
  }
  .task-badge.running { background: #1a2744; color: var(--accent); }
  .task-badge.completed { background: var(--green-dim); color: var(--green); }
  .task-badge.failed { background: var(--red-dim); color: var(--red); }
  .task-badge .spinner {
    width: 10px; height: 10px; border: 2px solid transparent;
    border-top-color: var(--accent); border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .task-meta {
    display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px;
  }
  .task-meta .tag {
    background: var(--bg-primary); padding: 2px 8px; border-radius: 4px;
    font-size: 11px; color: var(--text-faint); border: 1px solid var(--border);
  }

  /* Typing indicator */
  .typing-indicator {
    display: none; max-width: 900px; margin: 0 auto 20px;
    padding-left: 44px; font-size: 13px; color: var(--text-faint);
    align-items: center; gap: 8px;
  }
  .typing-indicator.active { display: flex; }
  .typing-dots { display: flex; gap: 3px; }
  .typing-dots span {
    width: 5px; height: 5px; background: var(--text-faint); border-radius: 50%;
    animation: blink 1.4s infinite;
  }
  .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
  .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes blink { 0%,80%,100% { opacity: 0.3; } 40% { opacity: 1; } }

  /* ---- Input area ---- */
  .input-area {
    border-top: 1px solid var(--border);
    background: var(--bg-secondary);
    padding: 16px 20px;
    flex-shrink: 0;
  }
  .input-row {
    max-width: 900px;
    margin: 0 auto;
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }
  .input-wrapper {
    flex: 1;
    background: var(--bg-input);
    border: 1px solid var(--border-light);
    border-radius: 12px;
    display: flex;
    align-items: flex-end;
    padding: 4px;
    transition: border-color 0.15s;
  }
  .input-wrapper:focus-within { border-color: var(--accent-dim); }
  .input-wrapper textarea {
    flex: 1;
    background: none;
    border: none;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 14px;
    line-height: 1.5;
    padding: 8px 12px;
    resize: none;
    outline: none;
    min-height: 22px;
    max-height: 200px;
  }
  .input-wrapper textarea::placeholder { color: var(--text-faint); }

  .send-btn {
    width: 40px; height: 40px; border-radius: 10px; border: none;
    background: var(--accent-dim); color: var(--accent);
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: all 0.15s; flex-shrink: 0;
  }
  .send-btn:hover { background: var(--accent); color: #fff; }
  .send-btn:disabled { opacity: 0.3; cursor: not-allowed; }
  .send-btn svg { width: 18px; height: 18px; }

  .input-hint {
    max-width: 900px; margin: 6px auto 0; font-size: 11px; color: var(--text-faint);
    display: flex; justify-content: space-between;
  }

  /* Quick actions */
  .quick-actions {
    max-width: 900px; margin: 0 auto 12px; display: flex; gap: 6px; flex-wrap: wrap;
  }
  .quick-btn {
    padding: 5px 12px; border-radius: 8px; border: 1px solid var(--border-light);
    background: var(--bg-tertiary); color: var(--text-muted); font-size: 12px;
    cursor: pointer; transition: all 0.15s;
  }
  .quick-btn:hover { background: var(--border); color: var(--text-primary); }

  /* Welcome screen */
  .welcome {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    height: 100%; padding: 40px; text-align: center;
  }
  .welcome h1 { font-size: 28px; color: var(--text-primary); margin-bottom: 8px; }
  .welcome h1 span { color: var(--accent); }
  .welcome p { color: var(--text-muted); font-size: 15px; max-width: 500px; line-height: 1.6; margin-bottom: 24px; }
  .welcome .suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 600px; }
  .welcome .suggestion {
    padding: 10px 16px; border-radius: 10px; border: 1px solid var(--border-light);
    background: var(--bg-tertiary); color: var(--text-secondary); font-size: 13px;
    cursor: pointer; transition: all 0.15s; text-align: left; max-width: 280px;
  }
  .welcome .suggestion:hover { border-color: var(--accent-dim); background: var(--bg-input); }
  .welcome .suggestion .title { font-weight: 600; color: var(--text-primary); margin-bottom: 2px; }
  .welcome .suggestion .desc { font-size: 12px; color: var(--text-muted); }

  /* Empty sidebar */
  .sidebar-empty { padding: 20px; text-align: center; color: var(--text-faint); font-size: 12px; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text-faint); }

  /* Responsive */
  @media (max-width: 768px) {
    .sidebar { position: absolute; z-index: 50; height: calc(100vh - 48px); }
    .sidebar.collapsed { width: 0; }
    .topbar-stats { display: none; }
  }
</style>
</head>
<body>

<!-- Top bar -->
<div class="topbar">
  <button class="sidebar-toggle" onclick="toggleSidebar()" title="Toggle sidebar">&#9776;</button>
  <div class="logo">Claude <span>Swarm</span></div>
  <div class="topbar-badges">
    <span class="badge online" id="status-badge">connecting...</span>
    <span class="badge backend" id="backend-badge">--</span>
  </div>
  <div class="topbar-stats">
    <div class="topbar-stat"><strong id="ts-workers">-</strong> workers</div>
    <div class="topbar-stat"><strong id="ts-instances">-</strong> instances</div>
    <div class="topbar-stat"><strong id="ts-running" style="color:var(--accent)">-</strong> running</div>
    <div class="topbar-stat"><strong id="ts-completed" style="color:var(--green)">-</strong> done</div>
    <div class="topbar-stat"><strong id="ts-failed" style="color:var(--red)">-</strong> failed</div>
  </div>
</div>

<!-- Main layout -->
<div class="main-layout">

  <!-- Sidebar: Swarm Activity -->
  <div class="sidebar" id="sidebar">
    <div class="sidebar-section">
      <h3>Instances <span class="count" id="sb-inst-count">0</span></h3>
      <div id="sb-instances"><div class="sidebar-empty">No instances</div></div>
    </div>
    <div class="sidebar-section" style="flex-shrink:0">
      <h3>Queue</h3>
      <div style="display:flex;gap:12px;font-size:12px;">
        <div><span style="color:var(--text-faint)">Total:</span> <strong id="sb-total">0</strong></div>
        <div><span style="color:var(--text-faint)">Queued:</span> <strong id="sb-queued" style="color:var(--yellow)">0</strong></div>
        <div><span style="color:var(--text-faint)">Running:</span> <strong id="sb-running" style="color:var(--accent)">0</strong></div>
      </div>
      <div style="margin-top:8px;height:4px;background:var(--border);border-radius:2px;overflow:hidden;">
        <div id="sb-progress" style="height:100%;background:linear-gradient(90deg,var(--accent-dim),var(--green));width:0%;transition:width 0.5s;border-radius:2px;"></div>
      </div>
      <div style="font-size:10px;color:var(--text-faint);margin-top:3px;text-align:right;" id="sb-pct">0%</div>
    </div>
    <div class="activity-feed" id="activity-feed">
      <div class="sidebar-section" style="border:none;padding:0;">
        <h3>Activity</h3>
      </div>
      <div class="sidebar-empty" id="activity-empty">No activity yet</div>
    </div>
  </div>

  <!-- Chat area -->
  <div class="chat-area">
    <div class="messages" id="messages">
      <div class="welcome" id="welcome-screen">
        <h1>Claude <span>Swarm</span></h1>
        <p>Submit tasks to your swarm of AI instances. Each message becomes a task processed by your local LLM fleet.</p>
        <div class="suggestions">
          <div class="suggestion" onclick="useSuggestion('Review the code quality and architecture of src/main.py')">
            <div class="title">Code Review</div>
            <div class="desc">Review code quality and architecture of a file</div>
          </div>
          <div class="suggestion" onclick="useSuggestion('Find all potential security vulnerabilities in the codebase')">
            <div class="title">Security Audit</div>
            <div class="desc">Scan for security vulnerabilities</div>
          </div>
          <div class="suggestion" onclick="useSuggestion('Analyze test coverage gaps and suggest missing test cases')">
            <div class="title">Test Analysis</div>
            <div class="desc">Find testing gaps and suggest improvements</div>
          </div>
          <div class="suggestion" onclick="useSuggestion('Review all Python imports and identify unused or circular dependencies')">
            <div class="title">Dependency Check</div>
            <div class="desc">Audit imports and dependency health</div>
          </div>
        </div>
      </div>
    </div>

    <div class="typing-indicator" id="typing">
      <div class="typing-dots"><span></span><span></span><span></span></div>
      <span>Swarm is processing...</span>
    </div>

    <div class="input-area">
      <div class="quick-actions" id="quick-actions" style="display:none;">
        <button class="quick-btn" onclick="sendQuick('/status')">Status</button>
        <button class="quick-btn" onclick="sendQuick('/instances')">Instances</button>
        <button class="quick-btn" onclick="sendQuick('/tasks')">Tasks</button>
        <button class="quick-btn" onclick="sendQuick('/clear')">Clear Chat</button>
      </div>
      <div class="input-row">
        <div class="input-wrapper">
          <textarea id="input" rows="1" placeholder="Send a task to the swarm..." autofocus></textarea>
        </div>
        <button class="send-btn" id="send-btn" onclick="sendMessage()" title="Send (Enter)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
      <div class="input-hint">
        <span>Enter to send &middot; Shift+Enter for new line &middot; /status /tasks /clear for commands</span>
        <span id="connection-status" style="color:var(--green)">connected</span>
      </div>
    </div>
  </div>
</div>

<script>
// ---- State ----
const API = window.location.origin;
let ws = null;
let chatMessages = [];
let taskMessageMap = {};  // task_id -> message index
let activeTasks = new Set();
let activityLog = [];
let sidebarOpen = true;
let streamThrottleTimer = null;

// ---- Utilities ----
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function renderMarkdown(text) {
  if (!text) return '';
  let html = esc(text);
  // Code blocks (``` ... ```)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    '<pre><code class="lang-' + lang + '">' + code.trim() + '</code></pre>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // Unordered lists
  html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, m => '<ul>' + m + '</ul>');
  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  // Blockquotes
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
  // Line breaks (double newline = paragraph)
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p>(<h[123]>)/g, '$1');
  html = html.replace(/(<\/h[123]>)<\/p>/g, '$1');
  html = html.replace(/<p>(<pre>)/g, '$1');
  html = html.replace(/(<\/pre>)<\/p>/g, '$1');
  html = html.replace(/<p>(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)<\/p>/g, '$1');
  html = html.replace(/<p>(<blockquote>)/g, '$1');
  html = html.replace(/(<\/blockquote>)<\/p>/g, '$1');
  return html;
}

function timeAgo(iso) {
  if (!iso) return '';
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 10) return 'just now';
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  return Math.floor(s/3600) + 'h ago';
}

function shortId(id) { return id ? id.substring(0, 8) : ''; }

// ---- Message rendering ----
function buildBodyHTML(msg) {
  let bodyContent = '';
  if (msg.extra.taskId) {
    const status = msg.extra.taskStatus || 'running';
    const spinnerHtml = status === 'running' ? '<div class="spinner"></div>' : '';
    bodyContent += `<div class="task-badge ${status}">${spinnerHtml}Task ${shortId(msg.extra.taskId)} - ${status}</div>`;
  }
  if (msg.role === 'user') {
    bodyContent += '<p>' + esc(msg.content) + '</p>';
  } else {
    bodyContent += renderMarkdown(msg.content);
  }
  // Render tool calls as collapsible blocks
  if (msg.extra.toolCalls && msg.extra.toolCalls.length > 0) {
    bodyContent += '<div class="tool-calls">';
    for (const tc of msg.extra.toolCalls) {
      const statusCls = tc.success ? 'ok' : 'err';
      const statusTxt = tc.success ? 'OK' : 'ERR';
      const argsStr = JSON.stringify(tc.args || {}, null, 2);
      bodyContent += `<div class="tool-call" onclick="this.classList.toggle('expanded')">
        <div class="tool-call-header">
          <span class="tool-arrow">&#9654;</span>
          <span class="tool-icon">&#9881;</span>
          <span class="tool-name">${esc(tc.tool)}(${Object.keys(tc.args||{}).map(k=>k+'=...').join(', ')})</span>
          <span class="tool-status ${statusCls}">${statusTxt}</span>
          <span class="tool-dur">${tc.duration_ms || 0}ms</span>
        </div>
        <div class="tool-call-body">${esc(argsStr)}</div>
      </div>`;
    }
    bodyContent += '</div>';
  }
  if (msg.extra.duration || msg.extra.backend || msg.extra.model || msg.extra.tokens || msg.extra.iterations) {
    bodyContent += '<div class="task-meta">';
    if (msg.extra.duration) bodyContent += `<span class="tag">${msg.extra.duration}</span>`;
    if (msg.extra.backend) bodyContent += `<span class="tag">${msg.extra.backend}</span>`;
    if (msg.extra.model) bodyContent += `<span class="tag">${msg.extra.model}</span>`;
    if (msg.extra.tokens) bodyContent += `<span class="tag">${msg.extra.tokens}</span>`;
    if (msg.extra.iterations) bodyContent += `<span class="tag">${msg.extra.iterations} iterations</span>`;
    bodyContent += '</div>';
  }
  return bodyContent;
}

function addMessage(role, content, extra = {}) {
  const idx = chatMessages.length;
  chatMessages.push({ role, content, extra, time: new Date().toISOString() });

  const container = document.getElementById('messages');
  const welcome = document.getElementById('welcome-screen');
  if (welcome) welcome.style.display = 'none';
  document.getElementById('quick-actions').style.display = 'flex';

  const msg = chatMessages[idx];
  const avatarIcon = role === 'user' ? 'U' : role === 'assistant' ? 'S' : 'i';
  const senderLabel = role === 'user' ? 'You' : role === 'assistant' ? 'Swarm' : 'System';

  const div = document.createElement('div');
  div.className = 'message ' + role;
  div.id = 'msg-' + idx;
  div.innerHTML = `<div class="avatar">${avatarIcon}</div>
    <div class="content">
      <div class="sender">${senderLabel}</div>
      <div class="body" id="msg-body-${idx}">${buildBodyHTML(msg)}</div>
    </div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return idx;
}

function updateMessage(idx, content, extra = {}) {
  if (idx < 0 || idx >= chatMessages.length) return;
  chatMessages[idx].content = content;
  Object.assign(chatMessages[idx].extra, extra);

  // Targeted DOM update - only touch the body element
  const bodyEl = document.getElementById('msg-body-' + idx);
  if (bodyEl) {
    bodyEl.innerHTML = buildBodyHTML(chatMessages[idx]);
    // Auto-scroll if near bottom
    const container = document.getElementById('messages');
    if (container.scrollHeight - container.scrollTop - container.clientHeight < 150) {
      container.scrollTop = container.scrollHeight;
    }
  }
}

// ---- API interactions ----
async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

async function postJSON(url, data) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ---- Send message / task ----
async function sendMessage() {
  const input = document.getElementById('input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  autoResize(input);

  // Handle commands
  if (text.startsWith('/')) {
    await handleCommand(text);
    return;
  }

  // Add user message
  addMessage('user', text);

  // Show typing indicator
  document.getElementById('typing').classList.add('active');

  try {
    // Submit as task
    const taskName = text.length > 50 ? text.substring(0, 47) + '...' : text;
    const result = await postJSON(API + '/tasks', {
      prompt: text,
      name: taskName,
      priority: 'normal'
    });

    const taskId = result.task_id;

    // Add assistant message placeholder
    const msgIdx = addMessage('assistant', 'Processing...', {
      taskId: taskId,
      taskStatus: 'running'
    });
    taskMessageMap[taskId] = msgIdx;
    activeTasks.add(taskId);

    addActivity('running', `Task submitted: ${taskName}`);

  } catch (e) {
    document.getElementById('typing').classList.remove('active');
    addMessage('system', 'Failed to submit task: ' + e.message);
  }
}

async function handleCommand(text) {
  const cmd = text.toLowerCase().split(' ')[0];

  switch (cmd) {
    case '/status': {
      addMessage('user', text);
      try {
        const status = await fetchJSON(API + '/status');
        const bs = status.tasks.by_status || {};
        const content = `**Swarm Status**\n\n` +
          `- **Running:** ${status.running ? 'Yes' : 'No'}\n` +
          `- **Workers:** ${status.workers}\n` +
          `- **Instances:** ${status.instances.total_instances} / ${status.instances.max_instances}\n` +
          `- **Tasks Running:** ${bs.running || 0}\n` +
          `- **Tasks Completed:** ${bs.completed || 0}\n` +
          `- **Tasks Failed:** ${bs.failed || 0}\n` +
          `- **Tasks Queued:** ${(bs.queued || 0) + (bs.pending || 0)}\n` +
          `- **Total Completed Tasks (all-time):** ${status.instances.total_completed_tasks}\n` +
          `- **Total Errors:** ${status.instances.total_errors}`;
        addMessage('assistant', content);
      } catch (e) {
        addMessage('system', 'Failed to get status: ' + e.message);
      }
      break;
    }
    case '/tasks': {
      addMessage('user', text);
      try {
        const tasks = await fetchJSON(API + '/tasks');
        if (tasks.length === 0) {
          addMessage('assistant', 'No tasks in the queue.');
        } else {
          let content = `**Tasks (${tasks.length})**\n\n`;
          content += '| Name | Status | Duration |\n|------|--------|----------|\n';
          for (const t of tasks) {
            const dur = t.duration_seconds ? t.duration_seconds.toFixed(1) + 's' : '-';
            content += `| ${t.name} | ${t.status} | ${dur} |\n`;
          }
          addMessage('assistant', content);
        }
      } catch (e) {
        addMessage('system', 'Failed to list tasks: ' + e.message);
      }
      break;
    }
    case '/instances': {
      addMessage('user', text);
      try {
        const instances = await fetchJSON(API + '/instances');
        if (instances.length === 0) {
          addMessage('assistant', 'No instances running.');
        } else {
          let content = `**Instances (${instances.length})**\n\n`;
          for (const i of instances) {
            content += `- **${shortId(i.id)}** - ${i.status} (${i.backend || 'claude'}`;
            if (i.model) content += ` / ${i.model}`;
            content += `) - ${i.completed_tasks} completed, ${i.error_count} errors\n`;
          }
          addMessage('assistant', content);
        }
      } catch (e) {
        addMessage('system', 'Failed to list instances: ' + e.message);
      }
      break;
    }
    case '/clear':
      chatMessages = [];
      taskMessageMap = {};
      activeTasks.clear();
      const mc = document.getElementById('messages');
      mc.innerHTML = '<div class="welcome" id="welcome-screen" style="display:flex"><h1>Claude <span>Swarm</span></h1><p>Chat cleared. Type a message to start a new task.</p></div>';
      document.getElementById('quick-actions').style.display = 'none';
      break;
    default:
      addMessage('system', `Unknown command: ${cmd}\n\nAvailable: /status, /tasks, /instances, /clear`);
  }
}

function sendQuick(cmd) {
  document.getElementById('input').value = cmd;
  sendMessage();
}

function useSuggestion(text) {
  document.getElementById('input').value = text;
  document.getElementById('input').focus();
}

// ---- Poll for task completion ----
async function pollTasks() {
  if (activeTasks.size === 0) return;

  for (const taskId of [...activeTasks]) {
    try {
      const task = await fetchJSON(API + '/tasks/' + taskId);

      if (task.status === 'completed') {
        activeTasks.delete(taskId);
        const msgIdx = taskMessageMap[taskId];
        const output = (task.result && task.result.output) ? task.result.output : 'Task completed (no output).';

        const extra = { taskId, taskStatus: 'completed' };
        if (task.duration_seconds) extra.duration = task.duration_seconds.toFixed(1) + 's';
        if (task.result && task.result.backend) extra.backend = task.result.backend;
        if (task.result && task.result.model) extra.model = task.result.model;
        if (task.result && task.result.usage) {
          const u = task.result.usage;
          const parts = [];
          if (u.input_tokens) parts.push('in: ' + u.input_tokens);
          if (u.output_tokens) parts.push('out: ' + u.output_tokens);
          if (parts.length) extra.tokens = parts.join(', ') + ' tokens';
        }
        if (task.result && task.result.tool_calls) extra.toolCalls = task.result.tool_calls;
        if (task.result && task.result.iterations) extra.iterations = task.result.iterations;

        updateMessage(msgIdx, output, extra);
        addActivity('completed', `Completed: ${task.name}`);

        if (activeTasks.size === 0) {
          document.getElementById('typing').classList.remove('active');
        }

      } else if (task.status === 'failed') {
        activeTasks.delete(taskId);
        const msgIdx = taskMessageMap[taskId];
        const errMsg = task.error || 'Unknown error';
        updateMessage(msgIdx, '**Task Failed**\n\n' + errMsg, {
          taskId, taskStatus: 'failed'
        });
        addActivity('failed', `Failed: ${task.name}`);

        if (activeTasks.size === 0) {
          document.getElementById('typing').classList.remove('active');
        }
      }
      // Still running - leave as is
    } catch (e) {
      // Ignore transient fetch errors
    }
  }
}

// ---- Sidebar updates ----
async function updateSidebar() {
  try {
    const [status, instances] = await Promise.all([
      fetchJSON(API + '/status'),
      fetchJSON(API + '/instances')
    ]);

    const bs = status.tasks.by_status || {};

    // Top bar badges
    const sb = document.getElementById('status-badge');
    sb.textContent = status.running ? 'ONLINE' : 'OFFLINE';
    sb.className = 'badge ' + (status.running ? 'online' : 'offline');

    const bb = document.getElementById('backend-badge');
    if (instances.length > 0 && instances[0].backend) {
      const m = instances[0].model || '';
      bb.textContent = instances[0].backend === 'ollama' ? 'ollama/' + m : 'claude-cli';
    }

    // Top bar stats
    document.getElementById('ts-workers').textContent = status.workers;
    document.getElementById('ts-instances').textContent = status.instances.total_instances;
    document.getElementById('ts-running').textContent = bs.running || 0;
    document.getElementById('ts-completed').textContent = bs.completed || 0;
    document.getElementById('ts-failed').textContent = bs.failed || 0;

    // Sidebar instances
    document.getElementById('sb-inst-count').textContent = instances.length;
    const instDiv = document.getElementById('sb-instances');
    if (instances.length === 0) {
      instDiv.innerHTML = '<div class="sidebar-empty">No instances</div>';
    } else {
      instDiv.innerHTML = instances.map(i => `
        <div class="instance-card">
          <div class="row">
            <span class="id">${shortId(i.id)}</span>
            <span class="pill ${i.status}">${i.status}</span>
          </div>
          ${i.current_task ? `<div class="task-label">${esc(i.current_task)}</div>` : ''}
          <div class="stat-row">
            <span class="mini-stat"><strong>${i.completed_tasks}</strong> done</span>
            <span class="mini-stat"><strong>${i.error_count}</strong> err</span>
            <span class="mini-stat">${i.backend || 'claude'}${i.model ? '/' + i.model : ''}</span>
          </div>
        </div>
      `).join('');
    }

    // Sidebar queue stats
    const total = status.tasks.total_tasks || 0;
    const done = (bs.completed || 0) + (bs.failed || 0);
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;

    document.getElementById('sb-total').textContent = total;
    document.getElementById('sb-queued').textContent = (bs.queued || 0) + (bs.pending || 0);
    document.getElementById('sb-running').textContent = bs.running || 0;
    document.getElementById('sb-progress').style.width = pct + '%';
    document.getElementById('sb-pct').textContent = total > 0 ? pct + '% (' + done + '/' + total + ')' : '0%';

    // Connection status
    document.getElementById('connection-status').textContent = 'connected';
    document.getElementById('connection-status').style.color = 'var(--green)';

  } catch (e) {
    document.getElementById('status-badge').textContent = 'OFFLINE';
    document.getElementById('status-badge').className = 'badge offline';
    document.getElementById('connection-status').textContent = 'disconnected';
    document.getElementById('connection-status').style.color = 'var(--red)';
  }
}

// ---- Activity log ----
function addActivity(type, text) {
  activityLog.unshift({ type, text, time: new Date() });
  if (activityLog.length > 50) activityLog.pop();
  renderActivity();
}

function renderActivity() {
  const feed = document.getElementById('activity-feed');
  const empty = document.getElementById('activity-empty');
  if (activityLog.length === 0) {
    if (empty) empty.style.display = 'block';
    return;
  }
  if (empty) empty.style.display = 'none';

  // Keep the header, replace items
  let html = '<div class="sidebar-section" style="border:none;padding:0;"><h3>Activity</h3></div>';
  for (const item of activityLog.slice(0, 30)) {
    html += `<div class="activity-item">
      <div class="activity-dot ${item.type}"></div>
      <div style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(item.text)}</div>
      <span class="activity-time">${timeAgo(item.time)}</span>
    </div>`;
  }
  feed.innerHTML = html;
}

// ---- Sidebar toggle ----
function toggleSidebar() {
  sidebarOpen = !sidebarOpen;
  document.getElementById('sidebar').classList.toggle('collapsed', !sidebarOpen);
}

// ---- Textarea auto-resize ----
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

// ---- Init ----
const input = document.getElementById('input');
input.addEventListener('input', () => autoResize(input));
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// WebSocket for real-time updates + streaming tokens
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws/stream');

  ws.onopen = () => {
    document.getElementById('connection-status').textContent = 'live';
    document.getElementById('connection-status').style.color = 'var(--green)';
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      // Streaming token from Ollama - throttled to avoid jitter
      if (data.type === 'token' && data.task_id) {
        const msgIdx = taskMessageMap[data.task_id];
        if (msgIdx !== undefined && activeTasks.has(data.task_id)) {
          // Store latest partial but only render at throttled rate
          chatMessages[msgIdx].content = data.partial;
          if (!streamThrottleTimer) {
            streamThrottleTimer = setTimeout(() => {
              streamThrottleTimer = null;
              const bodyEl = document.getElementById('msg-body-' + msgIdx);
              if (bodyEl) {
                bodyEl.innerHTML = buildBodyHTML(chatMessages[msgIdx]);
                const container = document.getElementById('messages');
                if (container.scrollHeight - container.scrollTop - container.clientHeight < 150) {
                  container.scrollTop = container.scrollHeight;
                }
              }
            }, 80);
          }
        }
        return;
      }

      // Real-time tool call event
      if (data.type === 'tool_call' && data.task_id) {
        const msgIdx = taskMessageMap[data.task_id];
        if (msgIdx !== undefined) {
          if (!chatMessages[msgIdx].extra.toolCalls) chatMessages[msgIdx].extra.toolCalls = [];
          chatMessages[msgIdx].extra.toolCalls.push(data);
        }
        addActivity('running', `Tool: ${data.tool}(${Object.keys(data.args||{}).join(',')})`);
        return;
      }

      // Task completion event from backend
      if (data.type === 'task_done' && data.task_id) {
        // pollTasks will pick up the final result with metadata
        return;
      }

      // Status update
      if (data.type === 'status' && data.running !== undefined) {
        const bs = data.tasks?.by_status || {};
        document.getElementById('ts-running').textContent = bs.running || 0;
        document.getElementById('ts-completed').textContent = bs.completed || 0;
        document.getElementById('ts-failed').textContent = bs.failed || 0;
      }
    } catch (e) {}
  };

  ws.onclose = () => {
    document.getElementById('connection-status').textContent = 'reconnecting...';
    document.getElementById('connection-status').style.color = 'var(--yellow)';
    setTimeout(connectWS, 3000);
  };

  ws.onerror = () => ws.close();
}

// Load existing tasks on startup
async function loadExistingTasks() {
  try {
    const tasks = await fetchJSON(API + '/tasks');
    if (tasks.length > 0) {
      addMessage('system', `Found **${tasks.length}** existing tasks from the current session.`);
      const running = tasks.filter(t => t.status === 'running');
      const completed = tasks.filter(t => t.status === 'completed');
      const failed = tasks.filter(t => t.status === 'failed');

      if (completed.length > 0 || failed.length > 0) {
        addActivity('completed', `${completed.length} tasks completed`);
      }
      if (running.length > 0) {
        addActivity('running', `${running.length} tasks still running`);
        // Track running tasks so we get their results
        for (const t of running) {
          const msgIdx = addMessage('assistant', 'Processing...', {
            taskId: t.id,
            taskStatus: 'running'
          });
          taskMessageMap[t.id] = msgIdx;
          activeTasks.add(t.id);
        }
        document.getElementById('typing').classList.add('active');
      }
      if (failed.length > 0) {
        addActivity('failed', `${failed.length} tasks failed`);
      }
    }
  } catch (e) {
    // Server might not be ready yet
  }
}

// Start everything
connectWS();
updateSidebar();
loadExistingTasks();

// Poll intervals
setInterval(updateSidebar, 3000);
setInterval(pollTasks, 2000);
setInterval(renderActivity, 30000);  // Re-render timestamps
</script>
</body>
</html>"""
