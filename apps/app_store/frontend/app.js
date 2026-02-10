/**
 * 通爻网络 App Store — 前端逻辑
 *
 * 核心功能：
 * 1. 展示网络状态（场景 + Agent）
 * 2. scope 过滤（全网 / 某个场景）
 * 3. 发起协商（带 scope 参数）
 * 4. 实时展示协商进度和方案
 */

const API_BASE = '';
let currentNegId = null;
let currentScope = 'all';
let ws = null;
let scenes = [];

// ============ 初始化 ============

document.addEventListener('DOMContentLoaded', () => {
    loadNetworkInfo();
    loadAgents('all');
});

async function loadNetworkInfo() {
    try {
        const resp = await fetch(`${API_BASE}/api/info`);
        const data = await resp.json();

        // 更新 header badges
        document.getElementById('badge-agents').textContent = `${data.total_agents} 个 Agent`;
        document.getElementById('badge-scenes').textContent = `${data.total_scenes} 个场景`;
        if (data.secondme_enabled) {
            document.getElementById('badge-secondme').style.display = 'inline-block';
        }

        // 渲染场景
        scenes = data.scenes || [];
        renderScenes(scenes);
        renderScopeTabs(scenes);
        renderScopeSelect(scenes);
    } catch (e) {
        console.warn('加载网络信息失败:', e);
    }
}

function renderScenes(sceneList) {
    const container = document.getElementById('scene-list');
    if (!sceneList.length) {
        container.innerHTML = '<div style="color: var(--text-muted);">暂无场景</div>';
        return;
    }
    container.innerHTML = sceneList.map(s => `
        <div class="scene-card" onclick="switchScope('scene:${s.scene_id}')">
            <div class="scene-card-name">${s.name}</div>
            <div class="scene-card-desc">${s.description}</div>
            <div class="scene-card-meta">
                <span class="badge badge-scene">${s.scene_id}</span>
                ${s.agent_count > 0 ? `<span class="badge">${s.agent_count} 人</span>` : ''}
            </div>
        </div>
    `).join('');
}

function renderScopeTabs(sceneList) {
    const tabs = document.getElementById('scope-tabs');
    let html = '<button class="scope-tab active" onclick="switchScope(\'all\')">全网</button>';
    for (const s of sceneList) {
        html += `<button class="scope-tab" onclick="switchScope('scene:${s.scene_id}')">${s.name}</button>`;
    }
    tabs.innerHTML = html;
}

function renderScopeSelect(sceneList) {
    const select = document.getElementById('scope-select');
    let html = '<option value="all">全网广播 — 所有 Agent 参与共振</option>';
    for (const s of sceneList) {
        html += `<option value="scene:${s.scene_id}">${s.name} — 只在此场景内</option>`;
    }
    select.innerHTML = html;
}

// ============ Agent 列表 ============

async function loadAgents(scope) {
    try {
        const resp = await fetch(`${API_BASE}/api/agents?scope=${encodeURIComponent(scope)}`);
        const data = await resp.json();
        renderAgents(data.agents);
        document.getElementById('agent-count').textContent =
            `共 ${data.count} 个 Agent` + (scope !== 'all' ? ` (${scope})` : '');
    } catch (e) {
        console.warn('加载 Agent 列表失败:', e);
    }
}

function renderAgents(agents) {
    const container = document.getElementById('agent-list');
    if (!agents.length) {
        container.innerHTML = '<div style="color: var(--text-muted);">该范围内暂无 Agent</div>';
        return;
    }
    container.innerHTML = agents.map(a => `
        <div class="agent-card">
            <div class="agent-card-name">${a.display_name}</div>
            <div class="agent-card-source">${a.source}</div>
            <div class="agent-card-scenes">
                ${(a.scene_ids || []).map(s => `<span class="badge badge-scene">${s}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

function switchScope(scope) {
    currentScope = scope;
    loadAgents(scope);

    // 更新 tab 激活状态
    document.querySelectorAll('.scope-tab').forEach(tab => {
        tab.classList.toggle('active',
            (scope === 'all' && tab.textContent === '全网') ||
            tab.onclick?.toString().includes(`'${scope}'`)
        );
    });

    // 同步 scope select
    document.getElementById('scope-select').value = scope;
}

// ============ 协商 ============

async function submitDemand() {
    const input = document.getElementById('demand-input');
    const intent = input.value.trim();
    if (!intent) {
        input.style.borderColor = 'var(--error)';
        setTimeout(() => { input.style.borderColor = ''; }, 2000);
        return;
    }

    const scope = document.getElementById('scope-select').value;
    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = '需求信号传播中...';

    // 清空之前的进度
    document.getElementById('timeline').innerHTML = '';
    document.getElementById('plan-section').style.display = 'none';

    try {
        const resp = await fetch(`${API_BASE}/api/negotiate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ intent, scope, user_id: 'app_store_user' }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        currentNegId = data.negotiation_id;

        // 显示协商状态
        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('status-scope').textContent = scope === 'all' ? '全网' : scope;
        setStatus('running', `协商进行中... (${data.agent_count} 个 Agent)`);

        addTimeline(
            '信号已广播',
            `需求已发送到 ${data.agent_count} 个 Agent (scope: ${scope})`,
            'formulation'
        );

        connectWS(currentNegId);
        pollStatus(currentNegId);
    } catch (e) {
        alert('提交失败: ' + e.message);
        btn.disabled = false;
        btn.textContent = '发出需求信号';
    }
}

// ============ WebSocket ============

function connectWS(negId) {
    if (ws) { ws.close(); ws = null; }
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
            break;
        case 'resonance.activated': {
            const count = data.activated_count || 0;
            addTimeline('共振激活', `${count} 个 Agent 产生共振`, 'resonance');
            break;
        }
        case 'offer.received': {
            const name = data.display_name || data.agent_id;
            const content = (data.content || '').substring(0, 150);
            addTimeline(`${name} 响应`, content + (content.length >= 150 ? '...' : ''), 'offer');
            break;
        }
        case 'barrier.complete':
            addTimeline('响应收集完成', `${data.offers_received || 0} 份响应，进入 Center 协调...`, 'barrier');
            break;
        case 'center.tool_call':
            if (data.tool_name !== 'output_plan') {
                addTimeline(`Center: ${data.tool_name}`, '', 'tool');
            }
            break;
        case 'plan.ready':
            showPlan(data.plan_text || '');
            setStatus('done', '协商完成');
            break;
    }
}

async function pollStatus(negId) {
    for (let i = 0; i < 120; i++) {
        await new Promise(r => setTimeout(r, 2000));
        if (!currentNegId || currentNegId !== negId) return;
        try {
            const resp = await fetch(`${API_BASE}/api/negotiate/${negId}`);
            const data = await resp.json();
            if (data.state === 'completed') {
                if (data.plan_output) showPlan(data.plan_output, data.participants);
                setStatus('done', '协商完成');
                const btn = document.getElementById('submit-btn');
                btn.disabled = false;
                btn.textContent = '重新发起协商';
                return;
            }
        } catch (e) { /* ignore */ }
    }
}

// ============ UI 工具 ============

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

function showPlan(text, participants) {
    document.getElementById('plan-section').style.display = 'block';
    document.getElementById('plan-text').textContent = text;

    // 展示参与者来源
    if (participants && participants.length > 0) {
        const html = participants.map(p => {
            const source = p.source || '';
            const score = p.resonance_score ? p.resonance_score.toFixed(3) : '';
            return `<span class="participant-tag">
                ${p.display_name}
                ${source ? `<span class="participant-source">${source}</span>` : ''}
                ${score ? `<span class="participant-score">${score}</span>` : ''}
            </span>`;
        }).join('');
        document.getElementById('plan-participants').innerHTML =
            `<div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">参与者：</div>${html}`;
    }

    document.getElementById('plan-section').scrollIntoView({ behavior: 'smooth' });
}

function setStatus(state, text) {
    document.getElementById('status-dot').className = `status-dot ${state}`;
    document.getElementById('status-text').textContent = text;
    document.getElementById('spinner').style.display = state === 'running' ? 'block' : 'none';
}
