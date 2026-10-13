/**
 * TMed-QA - Medical AI Frontend Logic
 * Agentic CRAG Interface Controller
 */

// API Base URL - auto detects current origin or defaults to http://127.0.0.1:7860
const API_BASE = window.location.protocol.startsWith('http') 
    ? window.location.origin 
    : 'http://127.0.0.1:7860';

// State Management
const state = {
    chatHistory: [],
    retrievedEvidence: [],
    sourcesList: [],
    uploadedNames: [],
    stagedFiles: [],
    isWaiting: false,
    theme: localStorage.getItem('tmed_theme') || 'light',
};

// DOM Elements
const DOM = {
    body: document.body,
    themeToggle: document.getElementById('theme-toggle-btn'),
    statusIndicator: document.getElementById('system-status-indicator'),
    statusText: document.getElementById('status-text'),
    sourceBadgeCount: document.getElementById('source-badge-count'),
    navTabs: document.querySelectorAll('.nav-tab'),
    tabPanes: document.querySelectorAll('.tab-pane'),

    // Chat
    chatContainer: document.getElementById('chat-messages-container'),
    messagesList: document.getElementById('messages-list'),
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    sendButton: document.getElementById('send-button'),
    welcomeCard: document.getElementById('welcome-card'),
    thinkingBubble: document.getElementById('thinking-bubble'),
    thinkingStatusText: document.getElementById('thinking-status-text'),
    btnClearChat: document.getElementById('btn-clear-chat'),
    btnRebuildQuick: document.getElementById('btn-rebuild-quick'),
    chipButtons: document.querySelectorAll('.chip-btn'),

    // Evidence
    evidencePanel: document.getElementById('evidence-panel'),
    evidenceCount: document.getElementById('evidence-count'),
    evidenceTiming: document.getElementById('evidence-timing-text'),
    evidenceList: document.getElementById('evidence-list'),
    emptyEvidence: document.getElementById('empty-evidence-placeholder'),

    // Sources
    fileDropZone: document.getElementById('file-drop-zone'),
    fileInput: document.getElementById('file-input'),
    browseFilesLink: document.getElementById('browse-files-link'),
    stagedFilesList: document.getElementById('staged-files-list'),
    stagedItems: document.getElementById('staged-items'),
    btnUploadSubmit: document.getElementById('btn-upload-submit'),
    uploadStatusMsg: document.getElementById('upload-status-msg'),
    deleteSelect: document.getElementById('delete-source-select'),
    btnDeleteSource: document.getElementById('btn-delete-source'),
    btnRefreshSources: document.getElementById('btn-refresh-sources'),
    btnRebuildFull: document.getElementById('btn-rebuild-full'),
    rebuildStatusMsg: document.getElementById('rebuild-status-msg'),
    sourcesTableBody: document.getElementById('sources-table-body'),
    sourceSearchInput: document.getElementById('source-search-input'),

    // Specs
    specEmbedding: document.getElementById('spec-embedding'),
    specLlm: document.getElementById('spec-llm'),
    specParams: document.getElementById('spec-params'),

    // Modal
    evidenceModal: document.getElementById('evidence-modal'),
    modalSourceType: document.getElementById('modal-source-type'),
    modalSourceTitle: document.getElementById('modal-source-title'),
    modalSectionTitle: document.getElementById('modal-section-title'),
    modalCharsCount: document.getElementById('modal-chars-count'),
    modalFullContent: document.getElementById('modal-full-content'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalDismissBtn: document.getElementById('modal-dismiss-btn'),
    modalCopyBtn: document.getElementById('modal-copy-btn'),

    // Toasts
    toastContainer: document.getElementById('toast-container'),
};

// ==========================================================================
// Initialization
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initTabs();
    initChatHandlers();
    initDropZone();
    initSourcesHandlers();
    initModalHandlers();

    // Fetch initial data
    loadSystemInfo();
    loadSources();
});

// ==========================================================================
// Theme Controller
// ==========================================================================

function initTheme() {
    DOM.body.setAttribute('data-theme', state.theme);
    DOM.themeToggle.addEventListener('click', () => {
        state.theme = state.theme === 'light' ? 'dark' : 'light';
        DOM.body.setAttribute('data-theme', state.theme);
        localStorage.setItem('tmed_theme', state.theme);
        showToast(`Đã chuyển sang chế độ ${state.theme === 'dark' ? 'Tối' : 'Sáng'}`, 'info');
    });
}

// ==========================================================================
// Navigation Tabs
// ==========================================================================

function initTabs() {
    DOM.navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetId = tab.getAttribute('data-tab');
            DOM.navTabs.forEach(t => t.classList.remove('active'));
            DOM.tabPanes.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.classList.add('active');

            if (targetId === 'tab-sources') {
                loadSources();
            }
        });
    });
}

// ==========================================================================
// Toast Notification Utility
// ==========================================================================

function showToast(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let iconSvg = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
    if (type === 'success') {
        iconSvg = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    } else if (type === 'error') {
        iconSvg = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
    }

    toast.innerHTML = `<span class="toast-icon">${iconSvg}</span> <span>${escapeHtml(message)}</span>`;
    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ==========================================================================
// Markdown Lightweight Parser
// ==========================================================================

function renderMarkdown(md) {
    if (!md) return '';
    let text = escapeHtml(md);

    // Code blocks ```code```
    text = text.replace(/```([\s\S]*?)```/g, (match, p1) => {
        return `<pre class="code-block"><code>${p1.trim()}</code></pre>`;
    });

    // Inline code `code`
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Horizontal Rule
    text = text.replace(/^---$/gm, '<hr>');

    // Headers
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold & Italic
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Blockquote
    text = text.replace(/^\&gt;\s?(.*$)/gim, '<blockquote>$1</blockquote>');

    // Numbered list items
    text = text.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<div class="list-item num"><strong>$1.</strong> $2</div>');

    // Bullet points
    text = text.replace(/^\s*[\-\*]\s+(.*$)/gim, '<div class="list-item bullet">&bull; $1</div>');

    // Clean line breaks
    text = text.replace(/\n\n+/g, '</p><p>');
    text = text.replace(/\n/g, '<br>');

    return `<p>${text}</p>`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ==========================================================================
// Chat Controller
// ==========================================================================

function initChatHandlers() {
    // Auto-resize textarea
    DOM.chatInput.addEventListener('input', () => {
        DOM.chatInput.style.height = 'auto';
        DOM.chatInput.style.height = Math.min(DOM.chatInput.scrollHeight, 160) + 'px';
    });

    // Handle Enter vs Shift+Enter
    DOM.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleChatSubmit();
        }
    });

    DOM.chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleChatSubmit();
    });

    // Quick suggestions & Hero chips
    document.querySelectorAll('.chip-btn, .hero-chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.getAttribute('data-query');
            if (query) {
                DOM.chatInput.value = query;
                handleChatSubmit();
            }
        });
    });

    // Clear chat
    DOM.btnClearChat.addEventListener('click', () => {
        if (confirm('Bạn có chắc muốn xóa toàn bộ lịch sử trò chuyện hiện tại?')) {
            state.chatHistory = [];
            state.retrievedEvidence = [];
            DOM.messagesList.innerHTML = '';
            if (DOM.welcomeCard) DOM.welcomeCard.style.display = 'block';
            if (DOM.emptyChatHero) DOM.emptyChatHero.style.display = 'flex';
            updateEvidencePanel([], 'Chưa có truy vấn');
            showToast('Đã xóa phiên trò chuyện', 'info');
        }
    });

    // Quick Rebuild
    DOM.btnRebuildQuick.addEventListener('click', handleRebuildStore);
}

async function handleChatSubmit() {
    const message = DOM.chatInput.value.trim();
    if (!message || state.isWaiting) return;

    // Reset input
    DOM.chatInput.value = '';
    DOM.chatInput.style.height = 'auto';
    if (DOM.welcomeCard) DOM.welcomeCard.style.display = 'none';
    if (DOM.emptyChatHero) DOM.emptyChatHero.style.display = 'none';

    // Append User Message Bubble
    appendMessageBubble('user', message);
    state.chatHistory.push({ role: 'user', content: message });

    // Show thinking indicator
    setThinkingState(true, 'Đang phân tích câu hỏi và truy xuất tri thức YHCT...');

    const startTime = Date.now();

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: state.chatHistory,
            }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Lỗi máy chủ (${response.status})`);
        }

        const data = await response.json();
        const elapsedSec = ((Date.now() - startTime) / 1000).toFixed(1);

        // Append Bot Message Bubble
        appendMessageBubble('bot', data.answer, elapsedSec);
        state.chatHistory.push({ role: 'assistant', content: data.answer });

        // Update Evidence Drawer
        state.retrievedEvidence = data.sources || [];
        updateEvidencePanel(state.retrievedEvidence, data.status || `Hoàn thành trong ${elapsedSec}s`);

    } catch (error) {
        console.error('Chat error:', error);
        appendMessageBubble('bot', `**Rất tiếc, đã xảy ra lỗi:** ${error.message}\n\n*Gợi ý:* Hãy kiểm tra kết nối máy chủ backend hoặc chạy lệnh \`python app.py\`.`);
        showToast(`Lỗi: ${error.message}`, 'error');
    } finally {
        setThinkingState(false);
    }
}

function appendMessageBubble(role, content, elapsed = null) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    if (role === 'user') {
        avatar.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;
    } else {
        avatar.innerHTML = `<img src="logo/TMed-QA.png" alt="TMed" onerror="this.src='/static/logo/TMed-QA.png'">`;
    }

    const bodyWrapper = document.createElement('div');
    bodyWrapper.className = 'msg-body-wrapper';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';

    if (role === 'user') {
        bubble.textContent = content;
    } else {
        bubble.innerHTML = renderMarkdown(content);
    }

    bodyWrapper.appendChild(bubble);

    // Meta Bar for Bot messages
    if (role === 'bot') {
        const metaBar = document.createElement('div');
        metaBar.className = 'msg-meta-bar';

        if (elapsed) {
            metaBar.innerHTML += `<span class="meta-time"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: -1px; margin-right: 3px;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>${elapsed}s</span> &bull; `;
        }
        metaBar.innerHTML += `<span>Agentic CRAG Verified</span>`;

        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-msg-btn';
        copyBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span>Sao chép</span>
        `;
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(content);
            copyBtn.innerHTML = `<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: -1px; margin-right: 3px;"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Đã chép</span>`;
            setTimeout(() => {
                copyBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    <span>Sao chép</span>
                `;
            }, 2000);
            showToast('Đã sao chép câu trả lời vào clipboard', 'success');
        });

        metaBar.appendChild(copyBtn);
        bodyWrapper.appendChild(metaBar);
    }

    row.appendChild(avatar);
    row.appendChild(bodyWrapper);
    DOM.messagesList.appendChild(row);

    // Scroll to bottom
    DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
}

function setThinkingState(waiting, text = '') {
    state.isWaiting = waiting;
    DOM.sendButton.disabled = waiting;
    if (waiting) {
        DOM.thinkingStatusText.textContent = text;
        DOM.thinkingBubble.style.display = 'flex';
        DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
    } else {
        DOM.thinkingBubble.style.display = 'none';
    }
}

// ==========================================================================
// Evidence Panel Controller
// ==========================================================================

function updateEvidencePanel(evidenceDocs, timingSummary = '') {
    DOM.evidenceCount.textContent = `${evidenceDocs.length} tài liệu`;
    DOM.evidenceTiming.textContent = timingSummary || 'Hoàn thành';

    if (!evidenceDocs || evidenceDocs.length === 0) {
        DOM.evidenceList.innerHTML = `
            <div class="empty-evidence">
                <div class="empty-icon">
                    <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                    </svg>
                </div>
                <p>Không có tài liệu minh chứng nào khớp với ngưỡng tương đồng trong truy vấn này.</p>
            </div>
        `;
        return;
    }

    DOM.evidenceList.innerHTML = '';
    evidenceDocs.forEach((doc, idx) => {
        const card = document.createElement('div');
        card.className = 'evidence-card';

        let badgeClass = 'badge-builtin';
        if (doc.type.includes('Upload')) badgeClass = 'badge-uploaded';
        if (doc.type.includes('Web')) badgeClass = 'badge-web';

        card.innerHTML = `
            <div class="evidence-card-top">
                <span class="evidence-type-badge ${badgeClass}">[${doc.id}] ${escapeHtml(doc.type)}</span>
                <span class="evidence-chars">${doc.chars} chars</span>
            </div>
            <div class="evidence-source-title">${escapeHtml(doc.source)}</div>
            <div class="evidence-section-name">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                </svg>
                <span>${escapeHtml(doc.section || 'Mục chung')}</span>
            </div>
            <div class="evidence-snippet">${escapeHtml(doc.preview)}</div>
            <div class="evidence-card-actions">
                <button class="btn-expand-evidence" data-index="${idx}">Xem chi tiết &rarr;</button>
            </div>
        `;

        const expandBtn = card.querySelector('.btn-expand-evidence');
        expandBtn.addEventListener('click', () => {
            openEvidenceModal(doc);
        });

        DOM.evidenceList.appendChild(card);
    });
}

// ==========================================================================
// Modal Controller
// ==========================================================================

function initModalHandlers() {
    DOM.modalCloseBtn.addEventListener('click', closeEvidenceModal);
    DOM.modalDismissBtn.addEventListener('click', closeEvidenceModal);
    DOM.evidenceModal.addEventListener('click', (e) => {
        if (e.target === DOM.evidenceModal) closeEvidenceModal();
    });

    DOM.modalCopyBtn.addEventListener('click', () => {
        const content = DOM.modalFullContent.textContent;
        navigator.clipboard.writeText(content);
        showToast('Đã sao chép toàn bộ trích dẫn', 'success');
    });
}

function openEvidenceModal(doc) {
    DOM.modalSourceType.textContent = doc.type;
    DOM.modalSourceTitle.textContent = doc.source;
    DOM.modalSectionTitle.textContent = doc.section || '-';
    DOM.modalCharsCount.textContent = `${doc.chars} ký tự`;
    DOM.modalFullContent.textContent = doc.content || doc.preview;
    DOM.evidenceModal.style.display = 'flex';
}

function closeEvidenceModal() {
    DOM.evidenceModal.style.display = 'none';
}

// ==========================================================================
// Sources & Ingestion Controller
// ==========================================================================

function initDropZone() {
    const zone = DOM.fileDropZone;
    const input = DOM.fileInput;

    DOM.browseFilesLink.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleSelectedFiles(e.dataTransfer.files);
        }
    });

    input.addEventListener('change', () => {
        if (input.files && input.files.length > 0) {
            handleSelectedFiles(input.files);
        }
    });
}

function handleSelectedFiles(fileList) {
    const validExts = ['.docx', '.txt', '.md'];
    for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i];
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (validExts.includes(ext)) {
            if (!state.stagedFiles.some(f => f.name === file.name)) {
                state.stagedFiles.push(file);
            }
        } else {
            showToast(`Bỏ qua tệp ${file.name}: Chỉ hỗ trợ .docx, .txt, .md`, 'error');
        }
    }
    renderStagedFiles();
}

function renderStagedFiles() {
    if (state.stagedFiles.length === 0) {
        DOM.stagedFilesList.style.display = 'none';
        DOM.btnUploadSubmit.disabled = true;
        return;
    }

    DOM.stagedFilesList.style.display = 'block';
    DOM.btnUploadSubmit.disabled = false;
    DOM.stagedItems.innerHTML = '';

    state.stagedFiles.forEach((file, index) => {
        const row = document.createElement('div');
        row.className = 'staged-item-row';
        row.innerHTML = `
            <span class="staged-file-item">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: -2px; margin-right: 5px;">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)</span>
            <button class="staged-remove-btn" title="Gỡ bỏ" data-index="${index}">&times;</button>
        `;
        row.querySelector('.staged-remove-btn').addEventListener('click', (e) => {
            const idx = parseInt(e.target.getAttribute('data-index'), 10);
            state.stagedFiles.splice(idx, 1);
            renderStagedFiles();
        });
        DOM.stagedItems.appendChild(row);
    });
}

function initSourcesHandlers() {
    DOM.btnUploadSubmit.addEventListener('click', handleUploadFiles);
    DOM.btnRefreshSources.addEventListener('click', () => {
        loadSources();
        showToast('Đã làm mới danh mục nguồn tri thức', 'info');
    });
    DOM.btnDeleteSource.addEventListener('click', handleDeleteSource);
    DOM.btnRebuildFull.addEventListener('click', handleRebuildStore);

    // Search filter in inventory table
    DOM.sourceSearchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        filterSourcesTable(query);
    });
}

async function loadSources() {
    try {
        const response = await fetch(`${API_BASE}/api/sources`);
        if (!response.ok) throw new Error('Không thể tải danh sách nguồn');
        const data = await response.json();

        state.sourcesList = data.sources || [];
        state.uploadedNames = data.uploaded || [];

        DOM.sourceBadgeCount.textContent = state.sourcesList.length;

        // Render Inventory Table
        renderSourcesTable(state.sourcesList);

        // Render Delete Dropdown
        renderDeleteDropdown(state.uploadedNames);

    } catch (error) {
        console.error('Error loading sources:', error);
        DOM.sourcesTableBody.innerHTML = `<tr><td colspan="5" class="table-loading">Lỗi kết nối máy chủ: ${error.message}</td></tr>`;
    }
}

function renderSourcesTable(sources) {
    if (!sources || sources.length === 0) {
        DOM.sourcesTableBody.innerHTML = `<tr><td colspan="5" class="table-loading">Chưa có nguồn dữ liệu nào được ghi nhận.</td></tr>`;
        return;
    }

    DOM.sourcesTableBody.innerHTML = '';
    sources.forEach((item, idx) => {
        const tr = document.createElement('tr');
        const statusBadge = item.status === 'Available'
            ? `<span class="status-badge-active">Hoạt động</span>`
            : `<span class="status-badge-missing">${escapeHtml(item.status)}</span>`;

        tr.innerHTML = `
            <td><strong>${idx + 1}</strong></td>
            <td><span class="badge-source-type">${escapeHtml(item.kind)}</span></td>
            <td><strong>${escapeHtml(item.name)}</strong></td>
            <td>${statusBadge}</td>
            <td><code style="font-size: 11.5px;">${escapeHtml(item.path)}</code></td>
        `;
        DOM.sourcesTableBody.appendChild(tr);
    });
}

function filterSourcesTable(query) {
    const rows = DOM.sourcesTableBody.querySelectorAll('tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    });
}

function renderDeleteDropdown(uploadedNames) {
    DOM.deleteSelect.innerHTML = `<option value="">-- Chọn tệp muốn xóa --</option>`;
    if (uploadedNames && uploadedNames.length > 0) {
        uploadedNames.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            DOM.deleteSelect.appendChild(opt);
        });
    }
}

async function handleUploadFiles() {
    if (state.stagedFiles.length === 0) return;

    DOM.btnUploadSubmit.disabled = true;
    DOM.uploadStatusMsg.textContent = 'Đang tải lên và xử lý phân đoạn văn bản...';

    const formData = new FormData();
    state.stagedFiles.forEach(file => {
        formData.append('files', file);
    });

    try {
        const response = await fetch(`${API_BASE}/api/sources/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Tải lên thất bại');
        }

        const data = await response.json();
        state.stagedFiles = [];
        renderStagedFiles();
        DOM.fileInput.value = '';

        DOM.uploadStatusMsg.textContent = data.message || 'Tải lên hoàn tất!';
        showToast(data.message || 'Đã nạp tài liệu thành công!', 'success');

        loadSources();

    } catch (error) {
        console.error('Upload error:', error);
        DOM.uploadStatusMsg.textContent = `Lỗi: ${error.message}`;
        showToast(`Lỗi tải lên: ${error.message}`, 'error');
    } finally {
        DOM.btnUploadSubmit.disabled = false;
    }
}

async function handleDeleteSource() {
    const filename = DOM.deleteSelect.value;
    if (!filename) {
        showToast('Vui lòng chọn một tệp tải lên để xóa', 'error');
        return;
    }

    if (!confirm(`Bạn có chắc muốn xóa tệp "${filename}" khỏi kho dữ liệu?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/sources/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename }),
        });

        if (!response.ok) throw new Error('Không thể xóa tệp');
        const data = await response.json();

        showToast(data.status || 'Đã xóa tệp thành công', 'success');
        loadSources();

    } catch (error) {
        console.error('Delete error:', error);
        showToast(`Lỗi khi xóa: ${error.message}`, 'error');
    }
}

async function handleRebuildStore() {
    if (state.isWaiting) return;

    const confirmRebuild = confirm('Tái lập Vector DB sẽ băm lại toàn bộ kho tài liệu và xây dựng lại cơ sở dữ liệu ChromaDB. Bạn có muốn tiếp tục?');
    if (!confirmRebuild) return;

    DOM.statusText.textContent = 'Đang tái lập Vector Store...';
    DOM.rebuildStatusMsg.textContent = 'Đang xử lý tạo embedding và nạp vào ChromaDB...';
    showToast('Bắt đầu tái lập Vector Store...', 'info');

    try {
        const response = await fetch(`${API_BASE}/api/sources/rebuild`, {
            method: 'POST',
        });

        if (!response.ok) throw new Error('Tái lập thất bại');
        const data = await response.json();

        DOM.rebuildStatusMsg.textContent = data.message || 'Tái lập thành công!';
        DOM.statusText.textContent = 'CRAG Sẵn sàng';
        showToast(data.message || 'Tái lập hoàn tất!', 'success');
        loadSources();

    } catch (error) {
        console.error('Rebuild error:', error);
        DOM.rebuildStatusMsg.textContent = `Lỗi: ${error.message}`;
        DOM.statusText.textContent = 'Lỗi hệ thống';
        showToast(`Lỗi tái lập: ${error.message}`, 'error');
    }
}

// ==========================================================================
// System Info & Specs
// ==========================================================================

async function loadSystemInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/system/info`);
        if (response.ok) {
            const data = await response.json();
            if (DOM.specEmbedding) DOM.specEmbedding.textContent = data.embedding_model || 'BAAI/bge-m3';
            if (DOM.specLlm) DOM.specLlm.textContent = `${data.llm_provider.toUpperCase()} (${data.llm_model})`;
            if (DOM.specParams) DOM.specParams.textContent = `Top-K = ${data.retrieval_k || 3} | Hybrid Thresh = 0.3`;
            DOM.statusText.textContent = 'CRAG Sẵn sàng';
        }
    } catch (err) {
        console.warn('System info unreachable:', err);
        DOM.statusText.textContent = 'Offline (Cần chạy server)';
    }
}
