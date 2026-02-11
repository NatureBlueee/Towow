/**
 * 通爻网络 — 产品面板
 *
 * 核心功能：
 * 1. 展示网络状态（场景 + Agent 画像）
 * 2. scope 过滤（全网 / 某个场景）— 场景是透镜，不是过滤器
 * 3. 场景差异化展示：不同场景强调不同的 Agent 信息
 * 4. 发起协商（带 scope 参数）
 * 5. 实时展示协商进度和方案
 * 6. SecondMe 登录（连接用户 AI 分身）
 * 7. 开发者模式：状态机视图 + API Playground + 事件监视器
 * 8. 图谱视图：径向布局可视化协商拓扑
 */

const API_BASE = '/store';
let currentNegId = null;
let currentScope = 'all';
let currentMode = 'experience';
let ws = null;
let scenes = [];

// ============ 事件数据层 ============

let eventStore = [];
let currentState = 'CREATED';
let graphAgents = [];
let graphCenterVisible = false;
let graphDone = false;

// ============ 场景展示配置 ============

const SCENE_DISPLAY = {
    hackathon: {
        color: '#F9A87C',
        highlight: (a) => {
            const parts = [];
            if (a.hackathon_history) parts.push(a.hackathon_history);
            if (a.availability) parts.push(a.availability);
            return parts.join(' · ');
        },
        tagSource: (a) => (a.skills || []).slice(0, 3),
        placeholder: '描述你想做的项目，需要什么技能的队友...',
    },
    recruitment: {
        color: '#8FD5A3',
        highlight: (a) => {
            const parts = [];
            if (a.experience_years) parts.push(`${a.experience_years}年经验`);
            if (a.expected_salary) parts.push(a.expected_salary);
            if (a.location) parts.push(a.location);
            return parts.join(' · ');
        },
        tagSource: (a) => {
            const tags = (a.skills || []).slice(0, 2);
            if (a.highlights && a.highlights.length > 0) tags.push(a.highlights[0]);
            return tags.slice(0, 3);
        },
        placeholder: '描述你的岗位需求，期望什么样的候选人...',
    },
    skill_exchange: {
        color: '#FFE4B5',
        highlight: (a) => {
            const parts = [];
            if (a.price_range) parts.push(a.price_range);
            if (a.availability) parts.push(a.availability);
            if (a.teaching_style) parts.push(a.teaching_style);
            return parts.join(' · ');
        },
        tagSource: (a) => (a.skills || []).slice(0, 3),
        placeholder: '你想学什么？或者你能教什么？',
    },
    matchmaking: {
        color: '#D4B8D9',
        highlight: (a) => {
            const parts = [];
            if (a.age) parts.push(`${a.age}岁`);
            if (a.personality) parts.push(a.personality);
            if (a.location) parts.push(a.location);
            return parts.join(' · ');
        },
        tagSource: (a) => (a.values || []).slice(0, 3),
        placeholder: '描述你理想的另一半，或者你自己是什么样的人...',
    },
};

const DEFAULT_DISPLAY = {
    color: '#8FD5A3',
    highlight: (a) => {
        if (a.experience) return a.experience;
        if (a.location) return a.location;
        return '';
    },
    tagSource: (a) => (a.skills || []).slice(0, 3),
    placeholder: '描述你的需求，网络中的 Agent 会通过共振响应...',
};

const SOURCE_COLORS = {
    secondme: '#F9A87C',
    json_file: '#C4A0CA',
    default: '#8FD5A3',
};

const SCENE_ACCENTS = ['#D4B8D9', '#8FD5A3', '#F9A87C', '#FFE4B5', '#B8D4E3'];

// ============ 工具函数 ============

function getSceneId() {
    if (currentScope.startsWith('scene:')) return currentScope.slice(6);
    return null;
}

function getSceneConfig() {
    const sid = getSceneId();
    return (sid && SCENE_DISPLAY[sid]) || DEFAULT_DISPLAY;
}

function getAvatarColor(agent) {
    const sid = getSceneId();
    if (sid && SCENE_DISPLAY[sid]) return SCENE_DISPLAY[sid].color;
    const source = agent.source || '';
    if (source.toLowerCase().includes('secondme')) return SOURCE_COLORS.secondme;
    if (source.toLowerCase().includes('json')) return SOURCE_COLORS.json_file;
    return SOURCE_COLORS.default;
}

function getInitial(name) {
    if (!name) return '?';
    return name.charAt(0).toUpperCase();
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ============ 示例需求 ============

const DEMAND_EXAMPLES = {
    hackathon: {
        scope: 'scene:hackathon',
        text: '我想做一个 AI 驱动的健康管理应用参加黑客松。我负责后端和机器学习（Python、PyTorch），需要找：\n\n1）一个前端/移动端开发，最好会 React Native\n2）一个有医疗健康领域知识的产品经理\n\n要求有黑客松经验，能 48 小时内快速出原型。',
    },
    cross: {
        scope: 'all',
        text: '我在做一个教育科技创业项目，正在组建早期团队：\n\n1）技术合伙人 — 全栈开发经验，最好懂 AI\n2）了解 K12 教育市场的产品人\n3）有用户增长经验的运营\n\n愿意给早期期权，不限地点，远程协作。',
    },
    skill: {
        scope: 'scene:skill_exchange',
        text: '我是 5 年经验的前端工程师，精通 React、TypeScript、Next.js。想学 Rust 和系统编程，转向底层开发方向。\n\n可以用前端开发辅导、代码审查和简历优化做交换。每周可安排 2-3 小时。',
    },
    recruit: {
        scope: 'scene:recruitment',
        text: '招聘高级 AI 工程师：\n\n- 3 年以上机器学习工程经验\n- 熟悉 PyTorch，有大规模模型训练和部署经验\n- 加分：NLP 方向、分布式训练经验\n\n远程工作，薪资 40-60 万，期权另谈。',
    },
};

function fillDemand(key) {
    const example = DEMAND_EXAMPLES[key];
    if (!example) return;
    document.getElementById('demand-input').value = example.text;
    document.getElementById('scope-select').value = example.scope;
    switchScope(example.scope);
}

// ============ SecondMe 登录 ============

function renderLoginState(user) {
    const loginBtn = document.getElementById('login-btn');
    const userInfo = document.getElementById('user-info');

    if (user && user.display_name) {
        loginBtn.style.display = 'none';
        userInfo.style.display = 'flex';
        document.getElementById('user-avatar').textContent = getInitial(user.display_name);
        document.getElementById('user-name').textContent = user.display_name;
    } else {
        loginBtn.style.display = '';
        userInfo.style.display = 'none';
    }
}

async function checkAuth() {
    try {
        // Auth 是平台级，路径 /api/auth/me，不走 API_BASE
        const resp = await fetch('/api/auth/me', { credentials: 'same-origin' });
        if (resp.ok) {
            const user = await resp.json();
            renderLoginState(user);
            return;
        }
    } catch {}
    renderLoginState(null);
}

async function loginWithSecondMe() {
    // 直接浏览器跳转到平台 auth，不再 fetch
    window.location.href = '/api/auth/secondme/start?return_to=/store/';
}

// ============ 初始化 ============

document.addEventListener('DOMContentLoaded', () => {
    loadNetworkInfo();
    loadAgents('all');
    checkAuth();
});

async function loadNetworkInfo() {
    try {
        const resp = await fetch(`${API_BASE}/api/info`);
        const data = await resp.json();

        document.getElementById('badge-agents').textContent = `${data.total_agents} 个 Agent`;
        document.getElementById('badge-scenes').textContent = `${data.total_scenes} 个场景`;

        scenes = data.scenes || [];
        renderScenes(scenes);
        renderScopeTabs(scenes);
        renderScopeSelect(scenes);
        renderPlaygroundScopes(scenes);
    } catch (e) {
        console.warn('加载网络信息失败:', e);
    }
}

// ============ 模式切换 ============

function switchMode(mode) {
    currentMode = mode;
    const expPanel = document.getElementById('experience-panel');
    const devPanel = document.getElementById('developer-panel');

    if (mode === 'experience') {
        expPanel.style.display = '';
        devPanel.style.display = 'none';
    } else {
        expPanel.style.display = 'none';
        devPanel.style.display = '';
    }

    document.querySelectorAll('.mode-tab').forEach(tab => {
        const isExp = tab.textContent.trim() === '体验';
        tab.classList.toggle('active',
            (mode === 'experience' && isExp) || (mode === 'developer' && !isExp)
        );
    });
}

// ============ 进度视图切换 ============

function switchProgressView(view) {
    const timelineView = document.getElementById('timeline-view');
    const graphView = document.getElementById('graph-view');

    if (view === 'timeline') {
        timelineView.style.display = '';
        graphView.style.display = 'none';
    } else {
        timelineView.style.display = 'none';
        graphView.style.display = '';
        renderGraphView();
    }

    document.querySelectorAll('#progress-view-tabs .scope-tab').forEach(tab => {
        const isTimeline = tab.textContent.trim() === '时间线';
        tab.classList.toggle('active',
            (view === 'timeline' && isTimeline) || (view === 'graph' && !isTimeline)
        );
    });
}

// ============ 场景卡片 ============

function renderScenes(sceneList) {
    const container = document.getElementById('scene-list');
    if (!container) return;
    if (!sceneList.length) {
        container.innerHTML = '<div class="empty-state">暂无场景</div>';
        return;
    }
    container.innerHTML = sceneList.map((s, i) => {
        const accent = SCENE_ACCENTS[i % SCENE_ACCENTS.length];
        const strategy = s.priority_strategy ? `<div class="scene-card-strategy">${escapeHtml(s.priority_strategy)}</div>` : '';
        return `
        <div class="scene-card" style="--scene-accent: ${accent}" onclick="switchScope('scene:${s.scene_id}')">
            <div class="scene-card-name">${escapeHtml(s.name)}</div>
            <div class="scene-card-desc">${escapeHtml(s.description)}</div>
            ${strategy}
            <div class="scene-card-meta">
                ${s.agent_count > 0 ? `<span class="badge badge-count">${s.agent_count} 人</span>` : ''}
            </div>
        </div>`;
    }).join('');
}

function renderScopeTabs(sceneList) {
    const tabs = document.getElementById('scope-tabs');
    let html = '<button class="scope-tab active" onclick="switchScope(\'all\')">全网</button>';
    for (const s of sceneList) {
        html += `<button class="scope-tab" onclick="switchScope('scene:${s.scene_id}')">${escapeHtml(s.name)}</button>`;
    }
    tabs.innerHTML = html;
}

function renderScopeSelect(sceneList) {
    const select = document.getElementById('scope-select');
    let html = '<option value="all">全网广播 — 所有 Agent 参与共振</option>';
    for (const s of sceneList) {
        html += `<option value="scene:${s.scene_id}">${escapeHtml(s.name)} — ${escapeHtml(s.description || '只在此场景内')}</option>`;
    }
    select.innerHTML = html;
}

function renderPlaygroundScopes(sceneList) {
    const select = document.getElementById('pg-agent-scope');
    if (!select) return;
    let html = '<option value="all">all</option>';
    for (const s of sceneList) {
        html += `<option value="scene:${s.scene_id}">scene:${escapeHtml(s.scene_id)}</option>`;
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
            `共 ${data.count} 个 Agent` + (scope !== 'all' ? ` (${scope.replace('scene:', '')})` : '');
    } catch (e) {
        console.warn('加载 Agent 列表失败:', e);
    }
}

function renderAgents(agents) {
    const container = document.getElementById('agent-list');
    if (!agents.length) {
        container.innerHTML = '<div class="empty-state">该范围内暂无 Agent</div>';
        return;
    }

    container.innerHTML = agents.map(a => {
        const color = getAvatarColor(a);
        const initial = getInitial(a.display_name);
        const name = escapeHtml(a.display_name);
        const tag = (a.skills || []).slice(0, 1).map(t => escapeHtml(String(t)))[0];

        return `
        <div class="agent-card">
            <div class="agent-avatar" style="background: ${color};">${initial}</div>
            <div class="agent-name">${name}</div>
            ${tag ? `<span class="agent-tag">${tag}</span>` : ''}
        </div>`;
    }).join('');
}

// ============ Scope 切换 ============

function switchScope(scope) {
    currentScope = scope;
    loadAgents(scope);

    document.querySelectorAll('.scope-tab').forEach(tab => {
        tab.classList.toggle('active',
            (scope === 'all' && tab.textContent === '全网') ||
            tab.onclick?.toString().includes(`'${scope}'`)
        );
    });

    document.getElementById('scope-select').value = scope;

    const config = getSceneConfig();
    document.getElementById('demand-input').placeholder = config.placeholder;
}

// ============ 协商 ============

async function submitDemand() {
    const input = document.getElementById('demand-input');
    const intent = input.value.trim();
    if (!intent) {
        input.style.borderColor = 'var(--c-warm)';
        setTimeout(() => { input.style.borderColor = ''; }, 2000);
        return;
    }

    const scope = document.getElementById('scope-select').value;
    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = '需求信号传播中...';

    document.getElementById('timeline').innerHTML = '';
    document.getElementById('plan-section').style.display = 'none';

    // Reset event store and graph state
    eventStore = [];
    currentState = 'CREATED';
    graphAgents = [];
    graphCenterVisible = false;
    graphDone = false;
    clearEventLog();
    renderStateView();
    renderGraphView();

    try {
        const headers = { 'Content-Type': 'application/json' };

        const resp = await fetch(`${API_BASE}/api/negotiate`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ intent, scope, user_id: 'app_store_user' }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        currentNegId = data.negotiation_id;

        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('status-scope').textContent = scope === 'all' ? '全网' : scope.replace('scene:', '');
        setStatus('running', `协商进行中... (${data.agent_count} 个 Agent)`);

        updateState('FORMULATING');

        addTimeline(
            '信号已广播',
            `需求已发送到 ${data.agent_count} 个 Agent (scope: ${scope === 'all' ? '全网' : scope.replace('scene:', '')})`,
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
    const url = `${protocol}//${location.host}/store/ws/${negId}`;
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

    // Store event for developer mode
    eventStore.push(event);
    appendEventLog(event);

    switch (type) {
        case 'formulation.ready':
            addTimeline('需求理解', data.formulated_text || data.raw_intent, 'formulation');
            updateState('FORMULATED');
            break;
        case 'resonance.activated': {
            const count = data.activated_count || 0;
            addTimeline('共振激活', `${count} 个 Agent 产生共振`, 'resonance');
            updateState('OFFERING');
            // Add agents to graph
            if (data.agents) {
                data.agents.forEach(a => {
                    const name = a.display_name || a.agent_id || '?';
                    if (!graphAgents.find(g => g.id === (a.agent_id || name))) {
                        graphAgents.push({ id: a.agent_id || name, name: name, active: false });
                    }
                });
            } else if (count > 0) {
                // If no agent list in event, create placeholders
                for (let i = graphAgents.length; i < count; i++) {
                    graphAgents.push({ id: `agent_${i}`, name: `A${i + 1}`, active: false });
                }
            }
            renderGraphView();
            break;
        }
        case 'offer.received': {
            const name = data.display_name || data.agent_id;
            const content = (data.content || '').substring(0, 200);
            addTimeline(`${name} 响应`, content + (content.length >= 200 ? '...' : ''), 'offer');
            // Mark agent as active in graph
            const agentId = data.agent_id || name;
            const found = graphAgents.find(g => g.id === agentId || g.name === name);
            if (found) {
                found.active = true;
            } else {
                graphAgents.push({ id: agentId, name: name, active: true });
            }
            renderGraphView();
            break;
        }
        case 'barrier.complete':
            addTimeline('响应收集完成', `${data.offers_received || 0} 份响应，进入 Center 协调...`, 'barrier');
            updateState('SYNTHESIZING');
            graphCenterVisible = true;
            renderGraphView();
            break;
        case 'center.tool_call':
            if (data.tool_name !== 'output_plan') {
                const desc = describeTool(data.tool_name, data.tool_args);
                addTimeline(`Center: ${desc}`, '', 'tool');
            }
            break;
        case 'plan.ready':
            showPlan(data.plan_text || '');
            setStatus('done', '协商完成');
            updateState('COMPLETED');
            graphDone = true;
            renderGraphView();
            break;
        case 'sub_negotiation.started':
            addTimeline('发现子需求', `正在探索: ${data.sub_demand || ''}`, 'tool');
            break;
    }

    renderStateView();
}

function describeTool(name, args) {
    switch (name) {
        case 'ask_agent': return `追问 ${(args && args.agent_id) || '某位 Agent'}`;
        case 'start_discovery': return '发起探索性对话';
        case 'create_sub_demand': return '识别缺口，触发子协商';
        case 'identify_gap': return '分析能力缺口';
        case 'request_info': return '请求补充信息';
        default: return name;
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
                updateState('COMPLETED');
                const btn = document.getElementById('submit-btn');
                btn.disabled = false;
                btn.textContent = '重新发起协商';
                return;
            }
        } catch (e) { /* ignore */ }
    }
}

// ============ 状态机视图 ============

const STATE_ORDER = [
    'CREATED', 'FORMULATING', 'FORMULATED', 'ENCODING',
    'OFFERING', 'BARRIER_WAITING', 'SYNTHESIZING', 'COMPLETED'
];

const STATE_EVENT_MAP = {
    'formulation.ready': 'FORMULATED',
    'resonance.activated': 'ENCODING',
    'offer.received': 'OFFERING',
    'barrier.complete': 'BARRIER_WAITING',
    'center.tool_call': 'SYNTHESIZING',
    'plan.ready': 'COMPLETED',
};

function updateState(newState) {
    if (newState && STATE_ORDER.includes(newState)) {
        currentState = newState;
    }
}

function renderStateView() {
    const currentIdx = STATE_ORDER.indexOf(currentState);
    document.querySelectorAll('.state-node').forEach(node => {
        const state = node.getAttribute('data-state');
        const stateIdx = STATE_ORDER.indexOf(state);
        node.classList.remove('state-active', 'state-passed');
        if (stateIdx === currentIdx) {
            node.classList.add('state-active');
        } else if (stateIdx < currentIdx) {
            node.classList.add('state-passed');
        }
    });
}

// ============ 图谱视图 ============

function renderGraphView() {
    const container = document.getElementById('graph-container');
    const svg = document.getElementById('graph-svg');
    if (!container || !svg) return;

    // Determine container size
    const containerWidth = container.offsetWidth || 300;
    const containerHeight = container.offsetHeight || 300;
    const cx = containerWidth / 2;
    const cy = containerHeight / 2;
    const radius = Math.min(cx, cy) - 40;

    svg.setAttribute('width', containerWidth);
    svg.setAttribute('height', containerHeight);

    // Remove old nodes (but keep SVG)
    container.querySelectorAll('.graph-node').forEach(n => n.remove());

    // Clear SVG lines
    svg.innerHTML = '';

    // Demand node (center)
    const demandNode = document.createElement('div');
    demandNode.className = 'graph-node graph-node-demand' + (graphDone ? ' graph-node-done' : '');
    demandNode.textContent = graphDone ? 'Done' : '需求';
    demandNode.style.left = (cx - 28) + 'px';
    demandNode.style.top = (cy - 28) + 'px';
    container.appendChild(demandNode);

    if (graphAgents.length === 0) return;

    // Agent nodes on circumference
    graphAgents.forEach((agent, i) => {
        const angle = (2 * Math.PI * i) / graphAgents.length - Math.PI / 2;
        const ax = cx + radius * Math.cos(angle);
        const ay = cy + radius * Math.sin(angle);

        const node = document.createElement('div');
        node.className = 'graph-node graph-node-agent' + (agent.active ? ' graph-node-active' : '');
        node.textContent = agent.name.length > 4 ? agent.name.substring(0, 3) + '..' : agent.name;
        node.title = agent.name;
        node.style.left = (ax - 22) + 'px';
        node.style.top = (ay - 22) + 'px';
        container.appendChild(node);

        // Line from center to agent
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', cx);
        line.setAttribute('y1', cy);
        line.setAttribute('x2', ax);
        line.setAttribute('y2', ay);
        line.setAttribute('class', agent.active ? 'graph-line graph-line-active' : 'graph-line');
        svg.appendChild(line);
    });

    // Center node (appears after barrier)
    if (graphCenterVisible) {
        // Place center node slightly offset from the true center
        const centerX = cx + 35;
        const centerY = cy - 35;
        const centerNode = document.createElement('div');
        centerNode.className = 'graph-node graph-node-center';
        centerNode.textContent = 'Center';
        centerNode.style.left = (centerX - 20) + 'px';
        centerNode.style.top = (centerY - 20) + 'px';
        container.appendChild(centerNode);

        // Lines from center node to active agents
        graphAgents.forEach((agent, i) => {
            if (!agent.active) return;
            const angle = (2 * Math.PI * i) / graphAgents.length - Math.PI / 2;
            const ax = cx + radius * Math.cos(angle);
            const ay = cy + radius * Math.sin(angle);

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', centerX);
            line.setAttribute('y1', centerY);
            line.setAttribute('x2', ax);
            line.setAttribute('y2', ay);
            line.setAttribute('class', 'graph-line graph-line-active');
            svg.appendChild(line);
        });
    }
}

// ============ 事件流监视器 ============

function appendEventLog(event) {
    const log = document.getElementById('event-log');
    if (!log) return;

    // Remove empty state on first event
    const emptyState = log.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const entry = document.createElement('div');
    entry.className = 'event-log-entry';
    const type = event.event_type || event.type || 'unknown';
    entry.innerHTML = `
        <span class="event-log-type">${escapeHtml(type)}</span>
        <pre class="event-log-json">${escapeHtml(JSON.stringify(event.data || event, null, 2))}</pre>
    `;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function clearEventLog() {
    const log = document.getElementById('event-log');
    if (!log) return;
    log.innerHTML = '<div class="empty-state">等待协商事件...</div>';
}

// ============ API Playground ============

const SCENE_TEMPLATES = {
    hackathon: {
        scene_id: 'hackathon_custom',
        name: '黑客松组队',
        description: '帮助参赛者找到最佳队友，互补技能快速组队',
        priority_strategy: '技术互补性优先',
        domain_context: '黑客松竞赛场景',
    },
    skill: {
        scene_id: 'skill_exchange_custom',
        name: '技能交换',
        description: '让人们互相教学，用自己的技能交换想学的技能',
        priority_strategy: '双向匹配度优先',
        domain_context: '技能交换与互助学习',
    },
    recruit: {
        scene_id: 'recruit_custom',
        name: '智能招聘',
        description: '帮企业找到合适的人，AI 辅助筛选和匹配',
        priority_strategy: '经验与岗位匹配优先',
        domain_context: '人才招聘与匹配',
    },
};

function fillSceneTemplate(key) {
    const tpl = SCENE_TEMPLATES[key];
    if (!tpl) return;
    document.getElementById('pg-scene-id').value = tpl.scene_id;
    document.getElementById('pg-scene-name').value = tpl.name;
    document.getElementById('pg-scene-desc').value = tpl.description;
    document.getElementById('pg-scene-strategy').value = tpl.priority_strategy;
    document.getElementById('pg-scene-domain').value = tpl.domain_context;
}

function togglePlayground(id) {
    const body = document.getElementById(`playground-${id}`);
    const icon = document.getElementById(`toggle-icon-${id}`);
    if (!body) return;
    const isHidden = body.style.display === 'none';
    body.style.display = isHidden ? '' : 'none';
    if (icon) icon.textContent = isHidden ? '-' : '+';
}

async function submitCreateScene() {
    const output = document.getElementById('resp-create-scene');
    output.classList.add('has-content');
    output.textContent = '请求中...';

    const payload = {
        scene_id: document.getElementById('pg-scene-id').value.trim(),
        name: document.getElementById('pg-scene-name').value.trim(),
        description: document.getElementById('pg-scene-desc').value.trim(),
        priority_strategy: document.getElementById('pg-scene-strategy').value.trim(),
        domain_context: document.getElementById('pg-scene-domain').value.trim(),
    };

    if (!payload.scene_id || !payload.name) {
        output.textContent = 'Error: scene_id 和 name 为必填项';
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/scenes/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        output.textContent = `${resp.status} ${resp.statusText}\n\n${JSON.stringify(data, null, 2)}`;
        // Refresh scene lists
        if (resp.ok) loadNetworkInfo();
    } catch (e) {
        output.textContent = `Error: ${e.message}`;
    }
}

async function submitListScenes() {
    const output = document.getElementById('resp-list-scenes');
    output.classList.add('has-content');
    output.textContent = '请求中...';

    try {
        const resp = await fetch(`${API_BASE}/api/scenes`);
        const data = await resp.json();
        output.textContent = `${resp.status} ${resp.statusText}\n\n${JSON.stringify(data, null, 2)}`;
    } catch (e) {
        output.textContent = `Error: ${e.message}`;
    }
}

async function submitListAgents() {
    const output = document.getElementById('resp-list-agents');
    output.classList.add('has-content');
    output.textContent = '请求中...';

    const scope = document.getElementById('pg-agent-scope').value;
    try {
        const resp = await fetch(`${API_BASE}/api/agents?scope=${encodeURIComponent(scope)}`);
        const data = await resp.json();
        output.textContent = `${resp.status} ${resp.statusText}\n\n${JSON.stringify(data, null, 2)}`;
    } catch (e) {
        output.textContent = `Error: ${e.message}`;
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
            <div class="timeline-title">${escapeHtml(title)}</div>
            <div class="timeline-detail">${escapeHtml(detail)}</div>
        </div>
    `;
    timeline.appendChild(item);
    item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showPlan(text, participants) {
    document.getElementById('plan-section').style.display = 'block';
    document.getElementById('plan-text').textContent = text;

    if (participants && participants.length > 0) {
        const html = participants.map(p => {
            const source = p.source || '';
            const score = p.resonance_score ? p.resonance_score.toFixed(3) : '';
            return `<span class="participant-tag">
                ${escapeHtml(p.display_name)}
                ${source ? `<span class="participant-source">${escapeHtml(source)}</span>` : ''}
                ${score ? `<span class="participant-score">${score}</span>` : ''}
            </span>`;
        }).join('');
        document.getElementById('plan-participants').innerHTML =
            `<div style="font-size:13px;color:var(--c-text-sec);margin-bottom:8px;">参与者：</div>${html}`;
    }

    document.getElementById('plan-section').scrollIntoView({ behavior: 'smooth' });
}

function setStatus(state, text) {
    document.getElementById('status-dot').className = `status-dot ${state}`;
    document.getElementById('status-text').textContent = text;
    document.getElementById('spinner').style.display = state === 'running' ? 'block' : 'none';
}
