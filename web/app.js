/* ============================================================
   OPENRESEARCH — APPLICATION LOGIC
   ============================================================ */

(function () {
  'use strict';

  // ============================================================
  // STATE
  // ============================================================
  const state = {
    conversations: JSON.parse(localStorage.getItem('openresearch_conversations') || '[]'),
    activeConvId: localStorage.getItem('openresearch_active_conv') || null,
    currentResearchId: null,
    isResearching: false,
    pollingInterval: null,
  };

  // ============================================================
  // DOM REFS
  // ============================================================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const el = {
    sidebar:          $('.sidebar'),
    conversationsList: $('#conversations-list'),
    emptyState:       $('#empty-state'),
    chatContainer:    $('#chat-container'),
    messages:         $('#messages'),
    inputForm:        $('#input-form'),
    inputField:       $('#input-field'),
    btnSend:          $('#btn-send'),
    btnNewChat:       $('#btn-new-chat'),
    btnThemeToggle:   $('#btn-theme-toggle'),
    themeLabel:       $('#theme-label'),
    btnClearChat:     $('#btn-clear-chat'),
    pipeline:         $('#pipeline'),
    pipelineSteps:    $('#pipeline-steps'),
    pipelineStatus:   $('#pipeline-status'),
    typingIndicator:  $('#typing-indicator'),
    toastContainer:   $('#toast-container'),
    chatHeaderQuery:  $('#chat-header-query'),
    chips:            $$('.chip'),
  };

  // ============================================================
  // API CLIENT
  // ============================================================
  const API = {
    async startResearch(query) {
      const res = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) throw new Error(`Research API error: ${res.status}`);
      return res.json();
    },

    async getStatus(rid) {
      const res = await fetch(`/api/research/${rid}/status`);
      if (!res.ok) throw new Error(`Status API error: ${res.status}`);
      return res.json();
    },

    async getResult(rid) {
      const res = await fetch(`/api/research/${rid}`);
      if (!res.ok) throw new Error(`Result API error: ${res.status}`);
      return res.json();
    },
  };

  // ============================================================
  // MARKDOWN PARSER (lightweight, no dependencies)
  // ============================================================
  function renderMarkdown(text) {
    if (!text) return '';

    let html = text
      // Escape HTML entities first
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')

      // Horizontal rules
      .replace(/^---$/gm, '<hr>')

      // Headings
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')

      // Bold and italic
      .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')

      // Inline code
      .replace(/`([^`]+)`/g, '<code>$1</code>')

      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')

      // Blockquotes
      .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')

      // Unordered lists
      .replace(/^[\*\-] (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')

      // Ordered lists
      .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')

      // Paragraphs - wrap consecutive non-list, non-heading lines
      .replace(/\n\n/g, '</p><p>')
      .replace(/^([^<].+)$/gm, function(m) {
        if (m.match(/^<(h[1-3]|ul|ol|li|blockquote|hr|pre)/)) return m;
        return m;
      });

    html = '<p>' + html + '</p>';
    html = html.replace(/<p><\/p>/g, '');

    return html;
  }

  // ============================================================
  // CONVERSATIONS
  // ============================================================
  function saveConversations() {
    localStorage.setItem('openresearch_conversations', JSON.stringify(state.conversations));
  }

  function getConversation(id) {
    return state.conversations.find(c => c.id === id);
  }

  function createConversation(query) {
    const conv = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      query: query,
      messages: [],
      createdAt: Date.now(),
      status: 'active',
    };
    state.conversations.unshift(conv);
    state.activeConvId = conv.id;
    saveConversations();
    renderConversations();
    return conv;
  }

  function addMessageToConv(convId, msg) {
    const conv = getConversation(convId);
    if (!conv) return;
    conv.messages.push(msg);
    conv.updatedAt = Date.now();
    saveConversations();
  }

  function updateConvStatus(convId, status) {
    const conv = getConversation(convId);
    if (!conv) return;
    conv.status = status;
    saveConversations();
    renderConversations();
  }

  function deleteConversation(id) {
    state.conversations = state.conversations.filter(c => c.id !== id);
    if (state.activeConvId === id) {
      state.activeConvId = null;
    }
    saveConversations();
    renderConversations();
  }

  // ============================================================
  // RENDER CONVERSATIONS
  // ============================================================
  function renderConversations() {
    const list = el.conversationsList;
    list.innerHTML = '';

    if (state.conversations.length === 0) {
      list.innerHTML = '<div class="conv-empty">No conversations yet</div>';
      return;
    }

    state.conversations.forEach(conv => {
      const btn = document.createElement('button');
      btn.className = 'conv-item' + (conv.id === state.activeConvId ? ' active' : '');
      btn.setAttribute('role', 'listitem');
      btn.dataset.convId = conv.id;

      const icon = conv.status === 'done'
        ? '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 7.5L6 10.5L11 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        : '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.2"/></svg>';

      btn.innerHTML = `
        <span class="conv-item-icon">${icon}</span>
        <span class="conv-item-text">${escapeHtml(conv.query.slice(0, 50))}</span>
        <span class="conv-item-status">
          <span class="conv-status-dot ${conv.status === 'active' ? 'active' : conv.status === 'done' ? 'done' : ''}"></span>
        </span>
      `;

      btn.addEventListener('click', () => {
        switchConversation(conv.id);
      });

      list.appendChild(btn);
    });
  }

  // ============================================================
  // SWITCH CONVERSATION
  // ============================================================
  function switchConversation(convId) {
    state.activeConvId = convId;
    localStorage.setItem('openresearch_active_conv', convId);
    renderConversations();

    const conv = getConversation(convId);
    if (!conv) return;

    // Show chat container
    el.emptyState.style.display = 'none';
    el.chatContainer.classList.add('active');

    // Clear and re-render messages
    el.messages.innerHTML = '';
    el.chatHeaderQuery.textContent = conv.query;

    conv.messages.forEach(msg => {
      appendMessageBubble(msg.role, msg.content, msg.sources, msg.confidence);
    });
  }

  // ============================================================
  // APPEND MESSAGE
  // ============================================================
  function appendMessageBubble(role, content, sources, confidence) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const avatar = role === 'user' ? 'U' : 'R';
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
      sourcesHtml = '<div class="message-sources">';
      sources.forEach((src, i) => {
        const label = typeof src === 'string' ? src : src.title || src.url || `Source ${i + 1}`;
        const url = typeof src === 'string' ? src : src.url || '#';
        sourcesHtml += `<a href="${url}" target="_blank" rel="noopener noreferrer" class="source-badge">
          <span class="source-num">${i + 1}</span> ${escapeHtml(label)}
        </a>`;
      });
      if (confidence != null) {
        const pct = Math.round(confidence * 100);
        sourcesHtml += `<span class="confidence-badge">${pct}% confidence</span>`;
      }
      sourcesHtml += '</div>';
    }

    div.innerHTML = `
      <div class="message-avatar" aria-hidden="true">${avatar}</div>
      <div class="message-content">
        <div class="message-bubble">${role === 'assistant' ? renderMarkdown(content) : escapeHtml(content)}</div>
        ${sourcesHtml}
        <span class="message-timestamp">${timestamp}</span>
      </div>
    `;

    el.messages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function appendUserMessage(content) {
    return appendMessageBubble('user', content, null, null);
  }

  function appendAssistantMessage(content, sources, confidence) {
    return appendMessageBubble('assistant', content, sources || [], confidence || null);
  }

  // ============================================================
  // SCROLL
  // ============================================================
  function scrollToBottom() {
    requestAnimationFrame(() => {
      el.messages.scrollTop = el.messages.scrollHeight;
    });
  }

  // ============================================================
  // PIPELINE
  // ============================================================
  const PIPELINE_STEPS = ['planner', 'search', 'extract', 'reason', 'synthesize'];
  const STEP_LABELS = {
    initializing:     'planner',
    planning:         'planner',
    searching:        'search',
    extracting:       'extract',
    chunking:         'extract',
    ranking:          'extract',
    reasoning:        'reason',
    synthesizing:     'synthesize',
    final_answer:     'synthesize',
  };

  function resetPipeline() {
    el.pipeline.hidden = true;
    el.pipelineStatus.textContent = '';
    $$('.pipeline-step').forEach(s => s.dataset.status = 'pending');
    $$('.pipeline-connector').forEach(c => c.classList.remove('done'));
  }

  function updatePipeline(stepName, statusText) {
    el.pipeline.hidden = false;

    const mapKey = Object.keys(STEP_LABELS).find(k => stepName.toLowerCase().includes(k))
      || stepName.toLowerCase();
    const currentStepIndex = PIPELINE_STEPS.indexOf(STEP_LABELS[mapKey] || 'planner');

    PIPELINE_STEPS.forEach((step, i) => {
      const el_step = el.pipelineSteps.querySelector(`[data-step="${step}"]`);
      if (!el_step) return;

      if (i < currentStepIndex) {
        el_step.dataset.status = 'done';
      } else if (i === currentStepIndex) {
        el_step.dataset.status = 'active';
      } else {
        el_step.dataset.status = 'pending';
      }
    });

    // Update connectors
    $$('.pipeline-connector').forEach((conn, i) => {
      conn.classList.toggle('done', i < currentStepIndex);
    });

    el.pipelineStatus.textContent = statusText || `Processing: ${stepName}`;
  }

  // ============================================================
  // TYPING INDICATOR
  // ============================================================
  function showTyping() {
    el.typingIndicator.hidden = false;
    scrollToBottom();
  }

  function hideTyping() {
    el.typingIndicator.hidden = true;
  }

  // ============================================================
  // TOAST
  // ============================================================
  function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = 'toast' + (type === 'error' ? ' error' : '');
    toast.textContent = message;
    el.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-8px)';
      toast.style.transition = 'all 300ms ease-out';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // ============================================================
  // RESEARCH FLOW
  // ============================================================
  async function startResearch(query) {
    if (state.isResearching) return;
    if (!query || !query.trim()) return;

    // Reset UI for new research
    el.emptyState.style.display = 'none';
    el.chatContainer.classList.add('active');

    // Create conversation
    const conv = createConversation(query.trim());
    state.activeConvId = conv.id;
    localStorage.setItem('openresearch_active_conv', conv.id);

    // Clear messages for new conversation
    el.messages.innerHTML = '';
    el.chatHeaderQuery.textContent = conv.query;
    renderConversations();

    // Add user message
    appendUserMessage(conv.query);

    // Show typing + pipeline
    showTyping();
    resetPipeline();

    state.isResearching = true;
    el.inputField.disabled = true;
    el.btnSend.disabled = true;

    try {
      // Start research
      const result = await API.startResearch(conv.query);
      state.currentResearchId = result.research_id;

      // Start polling
      await pollResearch(result.research_id, conv.id);
    } catch (err) {
      hideTyping();
      showToast(`Failed to start research: ${err.message}`, 'error');
      updateConvStatus(conv.id, 'error');
      state.isResearching = false;
      el.inputField.disabled = false;
      el.btnSend.disabled = false;
      el.inputField.focus();
    }
  }

  async function pollResearch(rid, convId) {
    return new Promise((resolve) => {
      let attempts = 0;
      const maxAttempts = 300; // ~5 minutes at 1s interval
      let lastContent = '';

      el.pollingInterval = setInterval(async () => {
        attempts++;
        try {
          const status = await API.getStatus(rid);

          // Update pipeline
          const stepName = status.current_step || '';
          const progress = status.progress || 0;
          updatePipeline(stepName, `${stepName} (${progress}%)`);

          // Append partial results if available
          if (status.search_results && status.search_results.length > 0) {
            // Just keep pipeline updated - results shown at end
          }

          // Handle completion
          if (status.status === 'complete') {
            clearInterval(el.pollingInterval);
            el.pollingInterval = null;

            // Fetch full result
            const fullResult = await API.getResult(rid);

            hideTyping();
            resetPipeline();
            el.pipeline.hidden = true;

            const answer = fullResult.final_answer || status.final_answer || 'Research complete. No answer was generated.';
            const sources = fullResult.sources || status.sources || [];
            const confidence = fullResult.confidence_score || status.confidence_score || 0;

            // Append the final answer
            appendAssistantMessage(answer, sources, confidence);

            // Update conversation
            const conv = getConversation(convId);
            if (conv) {
              conv.status = 'done';
              saveConversations();
              renderConversations();
            }

            state.isResearching = false;
            el.inputField.disabled = false;
            el.btnSend.disabled = false;
            el.inputField.focus();

            if (fullResult.total_time) {
              showToast(`Research completed in ${Math.round(fullResult.total_time)}s`);
            }

            resolve();
            return;
          }

          // Handle error
          if (status.status === 'error') {
            clearInterval(el.pollingInterval);
            el.pollingInterval = null;

            hideTyping();
            resetPipeline();
            showToast(`Research failed: ${status.error || 'Unknown error'}`, 'error');

            const conv = getConversation(convId);
            if (conv) {
              conv.status = 'error';
              saveConversations();
              renderConversations();
            }

            state.isResearching = false;
            el.inputField.disabled = false;
            el.btnSend.disabled = false;

            resolve();
            return;
          }

          // Add intermediate update if status step changed
          if (stepName && stepName !== lastContent && stepName !== 'initializing') {
            lastContent = stepName;
            // Update status in typing area
          }

        } catch (err) {
          if (attempts > 3) {
            // Only show error after multiple failures (initial requests may 404 briefly)
            console.warn('Poll error:', err.message);
          }

          if (attempts >= maxAttempts) {
            clearInterval(el.pollingInterval);
            el.pollingInterval = null;
            hideTyping();
            showToast('Research timed out. Please try again.', 'error');
            state.isResearching = false;
            el.inputField.disabled = false;
            el.btnSend.disabled = false;
            resolve();
          }
        }
      }, 1000);
    });
  }

  // ============================================================
  // INPUT HANDLING
  // ============================================================
  function autoResize() {
    el.inputField.style.height = 'auto';
    el.inputField.style.height = Math.min(el.inputField.scrollHeight, 160) + 'px';
  }

  function updateSendButton() {
    el.btnSend.disabled = !el.inputField.value.trim() || state.isResearching;
  }

  function handleSubmit(e) {
    if (e) e.preventDefault();
    const query = el.inputField.value.trim();
    if (!query || state.isResearching) return;

    el.inputField.value = '';
    el.inputField.style.height = 'auto';
    updateSendButton();
    startResearch(query);
  }

  // ============================================================
  // THEME
  // ============================================================
  function getPreferredTheme() {
    const saved = localStorage.getItem('openresearch_theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('openresearch_theme', theme);
    el.themeLabel.textContent = theme === 'dark' ? 'Light' : 'Dark';
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    setTheme(current === 'dark' ? 'light' : 'dark');
  }

  // ============================================================
  // NEW CONVERSATION
  // ============================================================
  function newConversation() {
    if (state.isResearching) {
      if (!confirm('Research is in progress. Start a new conversation?')) return;
    }

    // Clean up any existing polling
    if (el.pollingInterval) {
      clearInterval(el.pollingInterval);
      el.pollingInterval = null;
    }

    state.currentResearchId = null;
    state.isResearching = false;
    el.inputField.disabled = false;
    el.btnSend.disabled = true;

    el.chatContainer.classList.remove('active');
    el.emptyState.style.display = 'flex';
    el.messages.innerHTML = '';
    resetPipeline();
    hideTyping();
    el.inputField.value = '';
    el.inputField.style.height = 'auto';
    el.inputField.focus();
  }

  // ============================================================
  // CLEAR ALL
  // ============================================================
  function clearAll() {
    if (state.conversations.length === 0) return;
    if (!confirm('Clear all conversations?')) return;
    state.conversations = [];
    state.activeConvId = null;
    localStorage.removeItem('openresearch_active_conv');
    saveConversations();
    renderConversations();
    newConversation();
  }

  // ============================================================
  // MOBILE SIDEBAR
  // ============================================================
  let sidebarOverlay = null;

  function toggleMobileSidebar() {
    el.sidebar.classList.toggle('open');
    if (!sidebarOverlay) {
      sidebarOverlay = document.createElement('div');
      sidebarOverlay.className = 'sidebar-overlay';
      sidebarOverlay.addEventListener('click', () => {
        el.sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
      });
      document.body.appendChild(sidebarOverlay);
    }
    sidebarOverlay.classList.toggle('active');
  }

  // ============================================================
  // UTILITIES
  // ============================================================
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ============================================================
  // KEYBOARD SHORTCUTS
  // ============================================================
  function handleKeydown(e) {
    // Cmd/Ctrl + N: new conversation
    if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
      e.preventDefault();
      newConversation();
    }

    // Escape: close mobile sidebar
    if (e.key === 'Escape') {
      if (el.sidebar.classList.contains('open')) {
        el.sidebar.classList.remove('open');
        if (sidebarOverlay) sidebarOverlay.classList.remove('active');
      }
    }
  }

  // ============================================================
  // INIT
  // ============================================================
  function init() {
    // Theme
    setTheme(getPreferredTheme());

    // Render conversations
    renderConversations();

    // Restore active conversation
    if (state.activeConvId) {
      const conv = getConversation(state.activeConvId);
      if (conv) {
        switchConversation(state.activeConvId);
      }
    }

    // Event listeners
    el.inputForm.addEventListener('submit', handleSubmit);

    el.inputField.addEventListener('input', () => {
      autoResize();
      updateSendButton();
    });

    el.inputField.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    });

    el.btnNewChat.addEventListener('click', newConversation);
    el.btnThemeToggle.addEventListener('click', toggleTheme);
    el.btnClearChat.addEventListener('click', clearAll);
    document.addEventListener('keydown', handleKeydown);

    // Suggestion chips
    el.chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const query = chip.dataset.query;
        if (query) {
          el.inputField.value = query;
          updateSendButton();
          autoResize();
          handleSubmit();
        }
      });
    });

    // Window resize - auto focus
    el.inputField.focus();

    // System theme change
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem('openresearch_theme')) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    });

    updateSendButton();
  }

  // ============================================================
  // START
  // ============================================================
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
