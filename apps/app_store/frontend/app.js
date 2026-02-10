/**
 * 通爻网络 App Store — 前端逻辑
 *
 * 核心功能：
 * 1. 展示网络状态（场景 + Agent 画像）
 * 2. scope 过滤（全网 / 某个场景）— 场景是透镜，不是过滤器
 * 3. 场景差异化展示：不同场景强调不同的 Agent 信息
 * 4. 发起协商（带 scope 参数）
 * 5. 实时展示协商进度和方案
 */

const API_BASE = '';
let currentNegId = null;
let currentScope = 'all';
let ws = null;
let scenes = [];

// ============ 场景展示配置 ============
// 每个场景是一个透镜——决定展示 Agent 的哪些面

const SCENE_DISPLAY = {
    hackathon: {
        color: '#F9A87C',   // 珊瑚橙 — 活力
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
        color: '#8FD5A3',   // 薄荷绿 — 专业
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
        color: '#FFE4B5',   // 桃色 — 温暖
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
        color: '#D4B8D9',   // 玫瑰紫 — 浪漫
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

// Agent avatar 颜色 (按 source 映射)
const SOURCE_COLORS = {
    secondme: '#F9A87C',
    json_file: '#C4A0CA',
    default: '#8FD5A3',
};

// Scene 左边框颜色
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
    // 场景模式：用场景色
    const sid = getSceneId();
    if (sid && SCENE_DISPLAY[sid]) return SCENE_DISPLAY[sid].color;
    // 全网模式：按 source 映射
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
    // Sync scope tabs
    switchScope(example.scope);
}

// ============ API Key ============

function toggleApiKey() {
    const body = document.getElementById('api-key-body');
    const icon = document.getElementById('api-key-icon');
    const visible = body.style.display !== 'none';
    body.style.display = visible ? 'none' : 'block';
    icon.textContent = visible ? '+' : '−';
}

function saveApiKey(value) {
    if (value && value.trim()) {
        localStorage.setItem('towow_api_key', value.trim());
    } else {
        localStorage.removeItem('towow_api_key');
    }
}

function getApiKey() {
    return localStorage.getItem('towow_api_key') || '';
}

// ============ 初始化 ============

document.addEventListener('DOMContentLoaded', () => {
    loadNetworkInfo();
    loadAgents('all');
    // Restore saved API key
    const savedKey = getApiKey();
    if (savedKey) {
        const input = document.getElementById('api-key-input');
        if (input) input.value = savedKey;
    }
});

async function loadNetworkInfo() {
    try {
        const resp = await fetch(`${API_BASE}/api/info`);
        const data = await resp.json();

        document.getElementById('badge-agents').textContent = `${data.total_agents} 个 Agent`;
        document.getElementById('badge-scenes').textContent = `${data.total_scenes} 个场景`;
        if (data.secondme_enabled) {
            document.getElementById('badge-secondme').style.display = 'inline-flex';
        }

        scenes = data.scenes || [];
        renderScenes(scenes);
        renderScopeTabs(scenes);
        renderScopeSelect(scenes);
    } catch (e) {
        console.warn('加载网络信息失败:', e);
    }
}

// ============ 场景卡片 ============

function renderScenes(sceneList) {
    const container = document.getElementById('scene-list');
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

// ============ Agent 列表 (Enriched Cards) ============

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

    const config = getSceneConfig();

    container.innerHTML = agents.map(a => {
        const color = getAvatarColor(a);
        const initial = getInitial(a.display_name);
        const name = escapeHtml(a.display_name);
        const role = escapeHtml(a.role || '');

        // 场景适配的标签
        const tags = (config.tagSource(a) || []).slice(0, 3);
        const tagsHtml = tags.length > 0
            ? `<div class="agent-tags">${tags.map(t => `<span class="agent-tag">${escapeHtml(String(t))}</span>`).join('')}</div>`
            : '';

        // 场景适配的关键信息
        const highlight = config.highlight(a);
        const metaHtml = highlight
            ? `<div class="agent-meta"><span class="agent-meta-highlight">${escapeHtml(highlight)}</span></div>`
            : '';

        // Bio（如果有且当前无更具体的 meta）
        const bioHtml = a.bio && !highlight
            ? `<div class="agent-bio">${escapeHtml(a.bio)}</div>`
            : '';

        return `
        <div class="agent-card">
            <div class="agent-avatar" style="background: ${color};">${initial}</div>
            <div class="agent-info">
                <div class="agent-name">${name}</div>
                ${role ? `<div class="agent-role">${role}</div>` : ''}
                ${tagsHtml}
                ${metaHtml}
                ${bioHtml}
            </div>
        </div>`;
    }).join('');
}

// ============ Scope 切换 ============

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

    // 场景适配：更新需求输入框的 placeholder
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

    // 清空之前的进度
    document.getElementById('timeline').innerHTML = '';
    document.getElementById('plan-section').style.display = 'none';

    try {
        const headers = { 'Content-Type': 'application/json' };
        const apiKey = getApiKey();
        if (apiKey) headers['X-API-Key'] = apiKey;

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

        // 显示协商状态
        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('status-scope').textContent = scope === 'all' ? '全网' : scope.replace('scene:', '');
        setStatus('running', `协商进行中... (${data.agent_count} 个 Agent)`);

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
            const content = (data.content || '').substring(0, 200);
            addTimeline(`${name} 响应`, content + (content.length >= 200 ? '...' : ''), 'offer');
            break;
        }
        case 'barrier.complete':
            addTimeline('响应收集完成', `${data.offers_received || 0} 份响应，进入 Center 协调...`, 'barrier');
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
            break;
        case 'sub_negotiation.started':
            addTimeline('发现子需求', `正在探索: ${data.sub_demand || ''}`, 'tool');
            break;
    }
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

    // 展示参与者来源
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
