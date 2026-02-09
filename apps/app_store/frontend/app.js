/**
 * AToA 应用商城 — 前端逻辑
 *
 * 核心功能：
 * 1. 管理已注册应用
 * 2. 发现和注册新应用
 * 3. 发起跨应用联邦协商
 * 4. 实时展示协商进度和方案
 */

const API_BASE = '';
let currentNegId = null;
let ws = null;

// ============ 初始化 ============

document.addEventListener('DOMContentLoaded', () => {
    loadApps();
});

async function loadApps() {
    try {
        const resp = await fetch(`${API_BASE}/api/apps`);
        const data = await resp.json();
        renderApps(data.apps, data.total_agents);
    } catch (e) {
        console.warn('加载应用列表失败:', e);
    }
}

function renderApps(apps, totalAgents) {
    const container = document.getElementById('app-list');
    const totalEl = document.getElementById('total-agents');

    if (!apps || apps.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted);">暂无已注册应用，点击「发现应用」添加</div>';
        totalEl.textContent = '';
        return;
    }

    container.innerHTML = `<div class="app-grid">${apps.map(a => `
        <div class="app-card">
            <div class="app-card-name">${a.app_name}</div>
            <div class="app-card-scene">${a.scene_name || a.description || ''}</div>
            <span class="app-card-agents">${a.agent_count} 个 Agent</span>
            <div class="app-card-url">${a.base_url}</div>
        </div>
    `).join('')}</div>`;

    totalEl.textContent = `共 ${apps.length} 个应用，${totalAgents} 个 Agent 可响应`;
}

// ============ 发现应用 ============

function showDiscoverModal() {
    document.getElementById('discover-modal').style.display = 'flex';
}

function hideDiscoverModal() {
    document.getElementById('discover-modal').style.display = 'none';
    document.getElementById('discover-result').textContent = '';
}

function quickDiscover(url) {
    document.getElementById('discover-url').value = url;
    discoverApp();
}

async function discoverApp() {
    const url = document.getElementById('discover-url').value.trim();
    if (!url) return;

    const resultEl = document.getElementById('discover-result');
    resultEl.textContent = '发现中...';
    resultEl.style.color = 'var(--text-secondary)';

    try {
        const resp = await fetch(`${API_BASE}/api/apps/discover`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_url: url }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        resultEl.textContent = `${data.app.app_name} 注册成功（${data.app.agent_count} 个 Agent）`;
        resultEl.style.color = 'var(--success)';

        // 刷新应用列表
        await loadApps();
    } catch (e) {
        resultEl.textContent = `发现失败: ${e.message}`;
        resultEl.style.color = 'var(--error)';
    }
}

// ============ 联邦协商 ============

async function submitFederatedDemand() {
    const input = document.getElementById('demand-input');
    const intent = input.value.trim();
    if (!intent) {
        input.style.borderColor = 'var(--error)';
        setTimeout(() => { input.style.borderColor = ''; }, 2000);
        return;
    }

    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = '跨应用信号传播中...';

    try {
        const resp = await fetch(`${API_BASE}/api/federated/negotiate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ intent, user_id: 'app_store_user' }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        currentNegId = data.negotiation_id;

        // 显示跨应用 Agent 来源
        if (data.cross_app_agents && data.cross_app_agents.length > 0) {
            const apps = [...new Set(data.cross_app_agents.map(a => a.app_name))];
            addTimeline(
                '信号已广播',
                `需求信号已传播到 ${apps.length} 个应用: ${apps.join('、')}`,
                'formulation'
            );
        }

        document.getElementById('progress-section').style.display = 'block';
        setStatus('running', '跨应用协商进行中...');

        connectWS(currentNegId);
        pollStatus(currentNegId);
    } catch (e) {
        alert('提交失败: ' + e.message);
        btn.disabled = false;
        btn.textContent = '发出跨应用信号';
    }
}

// ============ WebSocket ============

function connectWS(negId) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/${negId}`;
    ws = new WebSocket(url);

    ws.onmessage = (event) => {
        try {
            handleEvent(JSON.parse(event.data));
        } catch (e) {
            console.warn('消息解析失败:', e);
        }
    };
    ws.onerror = (e) => console.warn('WS 错误:', e);
    ws.onclose = () => console.log('WS 关闭');
}

function handleEvent(event) {
    const type = event.event_type || event.type;
    const data = event.data || event;

    switch (type) {
        case 'formulation.ready':
            addTimeline('需求理解', data.formulated_text || data.raw_intent, 'formulation');
            autoConfirm();
            break;
        case 'resonance.activated':
            const agents = data.agents || [];
            addTimeline('共振激活', `${data.activated_count || 0} 个跨应用 Agent 响应`, 'resonance');
            break;
        case 'offer.received':
            const displayName = data.display_name || data.agent_id;
            addTimeline(
                `${displayName} 响应`,
                (data.content || '').substring(0, 150) + '...',
                'offer'
            );
            break;
        case 'barrier.complete':
            addTimeline('响应收集完成', `${data.offers_received || 0} 份跨应用响应，开始协商...`, 'barrier');
            break;
        case 'center.tool_call':
            if (data.tool_name !== 'output_plan') {
                addTimeline(`Center: ${data.tool_name}`, '', 'tool');
            }
            break;
        case 'plan.ready':
            showPlan(data.plan_text || '');
            setStatus('done', '跨应用协商完成');
            break;
    }
}

async function autoConfirm() {
    if (!currentNegId) return;
    try {
        await fetch(`${API_BASE}/api/federated/negotiate/${currentNegId}/confirm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
    } catch (e) { /* ignore */ }
}

async function pollStatus(negId) {
    for (let i = 0; i < 120; i++) {
        await new Promise(r => setTimeout(r, 2000));
        if (!currentNegId || currentNegId !== negId) return;
        try {
            const resp = await fetch(`${API_BASE}/api/federated/negotiate/${negId}`);
            const data = await resp.json();
            if (data.state === 'completed') {
                if (data.plan_output) showPlan(data.plan_output);
                setStatus('done', '跨应用协商完成');
                const btn = document.getElementById('submit-btn');
                btn.disabled = false;
                btn.textContent = '重新发起跨应用协商';
                return;
            }
        } catch (e) { /* ignore */ }
    }
}

// ============ UI ============

function addTimeline(title, detail, dotType) {
    const timeline = document.getElementById('timeline');
    const item = document.createElement('div');
    item.className = 'timeline-item';
    item.innerHTML = `
        <div class="timeline-dot dot-${dotType}"></div>
        <div class="timeline-content">
            <div class="timeline-title">${title}</div>
            <div class="timeline-detail">${detail}</div>
        </div>
    `;
    timeline.appendChild(item);
    item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showPlan(text) {
    document.getElementById('plan-section').style.display = 'block';
    document.getElementById('plan-text').textContent = text;
    document.getElementById('plan-section').scrollIntoView({ behavior: 'smooth' });
}

function setStatus(state, text) {
    document.getElementById('status-dot').className = `status-dot ${state}`;
    document.getElementById('status-text').textContent = text;
    document.getElementById('spinner').style.display = state === 'running' ? 'block' : 'none';
}
