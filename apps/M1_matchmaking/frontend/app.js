/**
 * M1 AI 相亲 — 前端逻辑
 *
 * 核心流程：
 * 1. 加载用户列表
 * 2. 提交匹配需求
 * 3. WebSocket 接收实时事件
 * 4. 展示协商进度和匹配方案
 */

const API_BASE = '';
let currentNegId = null;
let ws = null;

// ============ 初始化 ============

document.addEventListener('DOMContentLoaded', () => {
    loadAgents();
});

async function loadAgents() {
    try {
        const resp = await fetch(`${API_BASE}/api/agents`);
        const data = await resp.json();
        renderAgents(data.agents);
    } catch (e) {
        document.getElementById('agent-list').innerHTML =
            '<div style="color: var(--error);">加载用户失败</div>';
    }
}

function renderAgents(agents) {
    const container = document.getElementById('agent-list');
    container.innerHTML = agents.map(a => `
        <div class="agent-chip" id="agent-${a.agent_id}">
            <div class="agent-avatar">${a.name[0]}</div>
            <div>
                <div class="agent-name">${a.name}</div>
                <div class="agent-role">${a.role}</div>
            </div>
        </div>
    `).join('');
}

// ============ 提交需求 ============

async function submitDemand() {
    const input = document.getElementById('demand-input');
    const intent = input.value.trim();
    if (!intent) {
        input.style.borderColor = 'var(--error)';
        setTimeout(() => { input.style.borderColor = ''; }, 2000);
        return;
    }

    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = '信号发送中...';

    try {
        const resp = await fetch(`${API_BASE}/api/negotiate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ intent, user_id: 'matchmaker_user' }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        currentNegId = data.negotiation_id;

        // 显示进度面板
        document.getElementById('progress-section').style.display = 'block';
        setStatus('running', '协商进行中...');

        // 连接 WebSocket
        connectWS(currentNegId);

        // 轮询状态（WebSocket 的备份）
        pollStatus(currentNegId);

    } catch (e) {
        alert('提交失败: ' + e.message);
        btn.disabled = false;
        btn.textContent = '发出匹配信号';
    }
}

// ============ WebSocket ============

function connectWS(negId) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/${negId}`;

    ws = new WebSocket(url);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleEvent(data);
        } catch (e) {
            console.warn('WS 消息解析失败:', e);
        }
    };

    ws.onerror = (e) => console.warn('WS 错误:', e);
    ws.onclose = () => console.log('WS 连接关闭');
}

function handleEvent(event) {
    const type = event.event_type || event.type;
    const data = event.data || event;

    switch (type) {
        case 'formulation.ready':
            addTimeline('需求理解', data.formulated_text || data.raw_intent, 'formulation');
            // 自动确认（生产环境让用户确认）
            autoConfirm();
            break;

        case 'resonance.activated':
            const count = data.activated_count || 0;
            const agents = data.agents || [];
            addTimeline(
                `共振激活`,
                `${count} 位用户响应了你的信号`,
                'resonance'
            );
            // 高亮激活的 Agent
            agents.forEach(a => {
                const el = document.getElementById(`agent-${a.agent_id}`);
                if (el) el.classList.add('active');
            });
            break;

        case 'offer.received':
            addTimeline(
                `${data.display_name || data.agent_id} 响应`,
                (data.content || '').substring(0, 150) + '...',
                'offer'
            );
            break;

        case 'barrier.complete':
            addTimeline(
                '响应收集完成',
                `共收到 ${data.offers_received || 0} 份响应，开始协商...`,
                'barrier'
            );
            break;

        case 'center.tool_call':
            if (data.tool_name !== 'output_plan') {
                addTimeline(
                    `Center 调用: ${data.tool_name}`,
                    JSON.stringify(data.tool_args || {}).substring(0, 100),
                    'tool'
                );
            }
            break;

        case 'plan.ready':
            showPlan(data.plan_text || '方案生成中...');
            setStatus('done', '协商完成');
            break;

        default:
            console.log('未处理的事件:', type, data);
    }
}

// ============ 自动确认 ============

async function autoConfirm() {
    if (!currentNegId) return;
    try {
        await fetch(`${API_BASE}/api/negotiate/${currentNegId}/confirm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
    } catch (e) {
        console.warn('自动确认失败:', e);
    }
}

// ============ 轮询 ============

async function pollStatus(negId) {
    const maxPolls = 120;
    for (let i = 0; i < maxPolls; i++) {
        await new Promise(r => setTimeout(r, 2000));
        if (!currentNegId || currentNegId !== negId) return;

        try {
            const resp = await fetch(`${API_BASE}/api/negotiate/${negId}`);
            const data = await resp.json();

            if (data.state === 'completed') {
                if (data.plan_output && !document.getElementById('plan-section').style.display !== 'none') {
                    showPlan(data.plan_output);
                }
                setStatus('done', '协商完成');

                // 重新启用提交按钮
                const btn = document.getElementById('submit-btn');
                btn.disabled = false;
                btn.textContent = '重新匹配';
                return;
            }
        } catch (e) {
            console.warn('轮询失败:', e);
        }
    }
}

// ============ UI 辅助 ============

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
    const dot = document.getElementById('status-dot');
    const label = document.getElementById('status-text');
    const spinner = document.getElementById('spinner');

    dot.className = `status-dot ${state}`;
    label.textContent = text;
    spinner.style.display = state === 'running' ? 'block' : 'none';
}
