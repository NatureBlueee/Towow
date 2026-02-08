'use client';

import { useState, useEffect, useCallback } from 'react';
import styles from './journey.module.css';

// --- Data Types ---

interface Transformation {
  label: string;
  time: string;
  oneLiner: string;
  meaning: string;
}

interface Phase {
  num: number;
  name: string;
  dates: string;
  narrative: string;
  decisions: string[];
  corrections: string[];
  surprise: string;
  quote: string;
  quoteAuthor?: string;
  tags: { label: string; color: 'code' | 'design' | 'doc' | 'deploy' }[];
  stats: string;
}

interface Compact {
  num: number;
  date: string;
  title: string;
  detail: string;
}

interface Session {
  label: string;
  dateRange: string;
  color: string;
  compacts: Compact[];
}

// --- Data ---

const STATS = [
  { num: '19', label: '开发天数' },
  { num: '52', label: 'Git 提交' },
  { num: '41', label: '上下文压缩' },
  { num: '18', label: 'PRD 文档' },
  { num: '3', label: '对话会话' },
];

const TRANSFORMATIONS: Transformation[] = [
  {
    label: '从代码到本质',
    time: '2/4 转折',
    oneLiner: '停下来思考，比写代码更重要',
    meaning: '放弃工程师的惯性，承认"写出来"不等于"想清楚"',
  },
  {
    label: '从复杂到极简',
    time: '2/6 顿悟',
    oneLiner: '"投影即函数"——一个概念统一整个系统',
    meaning: '好的架构不是设计出来的复杂性，而是简单规则递归产生的复杂性',
  },
  {
    label: '从封闭到开放',
    time: '2/8 共建',
    oneLiner: '从自己做，到邀请社区共建',
    meaning: '协议本身就应该体现协议的价值——开放协作',
  },
];

const PHASES: Phase[] = [
  {
    num: 1,
    name: '探索与理解',
    dates: '1/21 - 1/22',
    narrative:
      '一切从理解 OpenAgents 框架开始。这不是一个"新项目启动"的故事，而是一个"站在巨人肩膀上找路"的过程。我们发现 ToWow 的生产环境偏离了 OpenAgents 的设计范式——自研的路由和 Mock 通道只打日志不通信。而 Raphael 演示项目虽然简单，却完整跑通了多 Agent 协作。修复了 Python 导入问题后，第一次看到 Agent 们自主协调工作，那一刻确认了方向：不要重新发明轮子，要基于已验证的模式来扩展。',
    decisions: [
      '选择以 Raphael 演示代码为基础，而非修复偏离框架的生产代码',
      '使用绝对导入 + PYTHONPATH 解决模块加载问题（工程上不优雅，但有效）',
      '确定"每个用户都是一个 Worker Agent"的方向',
    ],
    corrections: [],
    surprise:
      'ToWow 生产环境的 _MockChannelHandle 只打日志不通信——这不是 bug，而是架构选择错误的信号。偏离了成熟框架的代价比想象中大。',
    quote: '这个非常棒！！！',
    quoteAuthor: '创始人看到多 Agent 协作跑通后的反应',
    tags: [
      { label: 'OpenAgents', color: 'code' },
      { label: 'Python', color: 'code' },
    ],
    stats: '11 commits / 2 compacts',
  },
  {
    num: 2,
    name: '后端服务封装',
    dates: '1/27 - 1/29',
    narrative:
      '有了能跑的骨架，下一步是让它可用。SecondMe OAuth2 集成让用户能用真实身份登录；SQLite 数据层让注册信息能持久化；WebSocket 让状态变化能实时推送。这个阶段最重要的不是技术实现，而是创始人传递的设计理念——"Keep it simple"。当我们的技术方案过度设计（复杂的并发控制、细粒度的限流），创始人直接打断："过度的复杂了"、"自我揣测了"。服务器够强，用户够少，先让它能用。',
    decisions: [
      '使用 SQLite 而非 PostgreSQL（足够轻量，足以验证）',
      'OAuth2 数据单向流动：SecondMe -> ToWow（不把用户在 ToWow 的数据推回 SecondMe）',
      '技术方案从"生产级"简化为"验证级"',
    ],
    corrections: [
      '"过度的复杂了" —— 拒绝了包含速率限制、并发控制的复杂方案',
      '"自我揣测了" —— 不要替用户假设他们的需求和限制',
      '"Keep it simple" —— 最小可用比完美重要',
    ],
    surprise:
      'SecondMe API 不返回 openId 字段——与文档不符。用 email 作为替代标识符，绕过了这个问题。真实系统总有文档没说的意外。',
    quote: '不需要质疑那么多',
    quoteAuthor: '创始人对过度审慎的 Agent 的回应',
    tags: [
      { label: 'FastAPI', color: 'code' },
      { label: 'OAuth2', color: 'code' },
      { label: 'SQLite', color: 'code' },
    ],
    stats: '5 commits / 4 compacts',
  },
  {
    num: 3,
    name: '网站全栈开发',
    dates: '1/30',
    narrative:
      '这是整个历程中最密集的一天——20次提交，8次上下文压缩，从一个空白的 Next.js 项目到一个可部署的完整网站。首页6个板块的文字从"200字一屏"精简到"100字以内"；配色从冷灰调整到暖米白；布局从网格卡片改为流动渐变。最有意义的是 Demo 演示场景的设计：创始人否决了"独立音乐人打造演出"的方案，因为它不体现通爻的核心价值。改为"找技术合伙人"——用户以为需要一个人，协商后发现真正需要的是一种能力。这个演示场景本身就是通爻哲学的微缩版。',
    decisions: [
      'Next.js 16 + App Router + CSS Modules（不用 Tailwind，保留对样式的完全控制）',
      '移除网格/卡片设计，改用滚动渐变背景（"网格给人更多囚禁的秩序感"）',
      'Demo V2 的10阶段交互动画：从需求缩小为点到最终方案形成',
    ],
    corrections: [
      '"网站太冷/临床感" —— 从 #EEEEEE 冷灰到 #F8F6F3 暖米白，不仅是颜色，是气质',
      '"这个独立音乐人打造演出是完全没有用的东西" —— 演示必须体现哲学，不是随便找个场景',
      '"视角偏右...左边有大概百分之二十的部分看不到" —— 提醒关注细节',
    ],
    surprise:
      'React Strict Mode 导致 WebSocket 双挂载/卸载——组件挂载两次，第一次的 WebSocket 被第二次卸载清理掉。生产环境不会有这个问题，但开发时让人误以为 WebSocket 坏了。',
    quote: '你以为你要一个什么东西，结果发现你不需要。',
    quoteAuthor: '创始人定义"认知转变"',
    tags: [
      { label: 'Next.js', color: 'design' },
      { label: 'UI/UX', color: 'design' },
      { label: 'WebSocket', color: 'code' },
    ],
    stats: '20 commits / 8 compacts',
  },
  {
    num: 4,
    name: '部署与运维',
    dates: '1/31',
    narrative:
      '网站从本地跑通到线上可访问——Railway 后端 + Vercel 前端 + Cloudflare CDN。这是一个看起来"只是部署"但实际充满细节的阶段：OAuth 回调需要支持多个地址（本地和生产）、Cookie 的 SameSite 策略影响跨域认证、Vercel 的 Root Directory 要指向 monorepo 的子目录。每一个"小问题"都需要理解整个请求链路。部署不是终点，而是让所有人能看到的起点。',
    decisions: [
      '支持 USE_REAL_AGENTS 环境变量切换真实/模拟模式',
      'Cookie 安全策略通过环境变量控制（COOKIE_SECURE）',
      '保留 Experience V2 演示版本，同时创建 V3 真实 Agent 版本',
    ],
    corrections: [],
    surprise:
      'Vercel 在 monorepo 中找不到 Next.js 目录——需要在 Dashboard 设置 Root Directory 为 raphael/requirement_demo/towow-website。部署配置比代码更容易被忽视。',
    quote: '',
    tags: [
      { label: 'Railway', color: 'deploy' },
      { label: 'Vercel', color: 'deploy' },
      { label: 'CDN', color: 'deploy' },
    ],
    stats: '8 commits / 3 compacts',
  },
  {
    num: 5,
    name: '架构深度重构',
    dates: '2/4 - 2/6',
    narrative:
      '这是整个历程的分水岭。创始人说了一句话："设计得很理想，但架构就是出很多小错误。" 然后他做了一个出乎意料的决定——不是让我去修 bug，而是让我停下来读文档。三篇核心文档：白皮书、技术简报、设计日志。读完之后不是写代码，而是讨论。接下来3天，14次上下文压缩，全部用于架构思考。从签名广播的 HDC 超向量编码，到 Agent 接入的多源适配器，到 Skill 系统的"提案-聚合"范式，到 WOWOK 区块链协议的集成——每一轮讨论都是对"本质是什么"的追问。最后一轮讨论 Service Agent 结晶机制时，创始人说"本质和实现没有区分开来，不应该这么复杂"。然后，在多次思维跳跃后，"投影即函数"诞生了——Agent 不是对象，而是函数结果；投影是唯一的基本操作。',
    decisions: [
      '三层共振过滤：Bloom Filter (O(1)) -> HDC 共振 (O(D)) -> LLM (O(model))',
      '"代码保障 > Prompt 保障"：凡是能用代码保障的确定性逻辑，绝不用 prompt',
      '多轮辩论是净负面（-3.5%，DeepMind 2025），但并行提案->聚合是正面（+57-81%）',
      'WOWOK 区块链作为"回声"机制——波浪出去了，必须回来',
      '"投影即函数"：消除了 Profile 更新算法、防漂移机制、状态维护、冷启动问题',
    ],
    corrections: [
      '"不要为了做MVP而做MVP，不要为了单纯的削减功能而用削减功能" —— 最小完整单元 != 砍功能',
      '"你只是给我执行了，但你没有想清楚" —— 不要先写再想，要先想再写',
      '"先讨论确认理解，再写文档" —— 对齐 > 效率',
      '"本质和实现没有区分开来" —— 催生了"投影即函数"',
      '"有些问题本身就不该出现" —— 最好的解决方案是消除问题本身',
    ],
    surprise:
      '研究发现 LLM 的"第一提案偏见"高达 10-30 倍（Microsoft 2025）——这不是 prompt 能解决的，必须用代码（等待屏障）保障。',
    quote: '设计得很理想，但架构就是出很多小错误。',
    quoteAuthor: '触发转变的那句话',
    tags: [
      { label: '架构设计', color: 'doc' },
      { label: 'Design Log', color: 'doc' },
      { label: 'Arch Skill', color: 'doc' },
    ],
    stats: '1 commit / 14 compacts',
  },
  {
    num: 6,
    name: '黑客松工具链',
    dates: '2/7',
    narrative:
      '架构想清楚之后，回到工程——但这次不一样了。每个工具都先用 arch skill 的方法论思考"做什么"和"为什么做"，然后才开始实现。Team Matcher 不是"组队匹配"，而是"协作可能性发现引擎"；Guide 不是"教程"，而是"认知透镜"。最戏剧化的时刻是应用卡在"广播中..."无反应——测试通过但实际不工作，mock 数据掩盖了真实的集成失败。创始人爆发了："mock模式不重要，直接变成应用！" 这句话与架构讨论中的"不要模拟"一脉相承。',
    decisions: [
      '使用 Opus 4.6 并行 Agent 开发（最多9个同时工作）',
      'SecondMe Chat API 集成：登录后 AI 基于 Profile 自动建议表单值',
      '放弃 mock 模式优先的策略，直接面对真实集成的复杂性',
    ],
    corrections: [
      '"mock模式不重要，直接变成应用" —— 不要为了演示而演示',
      '"不要说什么模拟五个Agent去响应" —— 同上',
      '明确要求用 Opus 4.6 而非 Sonnet 4.5 —— 质量 > 速度',
    ],
    surprise:
      '并行 Agent 开发的核心问题不是代码质量，而是接口对齐。4个 Agent 独立开发，产生了5个集成 Bug（WebSocket 消息被丢弃、Channel ID 不匹配、字段名不一致等）。需要一个"跨边界审查者"角色。',
    quote:
      'mock模式不重要，我需要全部的登陆啥的，直接做能用的，不是为了mock而mock',
    quoteAuthor: '创始人',
    tags: [
      { label: 'Team Matcher', color: 'code' },
      { label: 'SecondMe API', color: 'code' },
      { label: 'Full Stack', color: 'design' },
    ],
    stats: '1 commit / 8 compacts',
  },
  {
    num: 7,
    name: '共建任务体系',
    dates: '2/8',
    narrative:
      '19天的最后一天，把所有成果打开给社区。33个初始任务用架构评估精简为18个——"不是为了有任务而有任务"。9个 Opus 4.6 Agent 并行编写全部18篇 PRD，每个 Agent 使用 arch + task-arch skill 确保哲学对齐。/contribute 页面经历了三次迭代：第一版太花哨，第二版太简洁，创始人说"不是为了简洁而简洁"——每一层信息都有存在的理由，移除任何一层会丢失意义。这个设计原则恰好就是通爻自身的 Section 0.9（完备性 != 完全性）的具体化。一次提交，165个文件，+18,795行。',
    decisions: [
      '33->18 任务精简：用架构原则（"这个任务的本质是什么？它解决的问题是真实的吗？"）筛选',
      '飞书为主 + 网站为辅的共建策略（Bitable 管理 + build in public）',
      'PRD 写作使用 arch skill 方法论，确保"技术细节的背后有世界观"',
    ],
    corrections: [
      '"不是为了有任务而有任务" —— 33->18 不是因为数量太多，而是价值不够',
      '"不是为了简洁而简洁" —— 极度简单但保留完整意义（三次页面迭代的核心教训）',
      '纠正了 AI 对架构设计承诺的误解 —— "你误解了设计承诺的含义"',
    ],
    surprise:
      '9个 Agent 并行写 PRD 时，每个 Agent 对"通爻哲学"的理解略有不同——这本身就是"投影"的一个实例：同一个架构文档，通过不同的 Agent "透镜"，产生不同但各有价值的 PRD。',
    quote: '不是为了简洁而简洁。',
    quoteAuthor: '与 Section 0.9 完美对应的设计原则',
    tags: [
      { label: '18 PRDs', color: 'doc' },
      { label: '/contribute', color: 'design' },
      { label: 'Feishu', color: 'doc' },
      { label: 'Deploy', color: 'deploy' },
    ],
    stats: '1 commit (165 files, +18,795 lines) / 4 compacts',
  },
];

const SESSIONS: Session[] = [
  {
    label: '会话 1',
    dateRange: '主开发会话 / 1/26 - 2/5',
    color: '#8B6A90',
    compacts: [
      { num: 1, date: '1/26', title: '理解项目 + 修复 OpenAgents 导入问题 + 成功跑通多 Agent 协作', detail: '第一次深入 ToWow 代码。对比发现 Raphael 演示用原生 OpenAgents 模式（事件驱动、BaseMod），而生产环境偏离了框架（自研路由、Mock 通道只打日志）。Python 相对导入问题阻止了 Mod 加载，用 sys.path 操作绕过。修复后完整跑通了需求提交、频道创建、Agent邀请、任务分发、协调汇总的流程。' },
      { num: 2, date: '1/27', title: 'SecondMe OAuth2 登录 + 动态 Agent 创建', detail: '创建 Web 注册服务，接入 SecondMe OAuth2 授权码流程。用户登录后自动创建 Worker Agent 并注册到网络。完整的安全审查发现8个问题，全部修复。17个单元测试通过。' },
      { num: 3, date: '1/27', title: 'GitHub 上传 + OAuth 测试 + URL 编码问题修复', detail: '配置 .gitignore 排除大文件，推送到 GitHub。测试 SecondMe OAuth 流程时发现回调地址被双重编码，移除手动编码修复。发现 SecondMe API 不返回文档中的 openId 字段，改用 email 做标识符。' },
      { num: 4, date: '1/29', title: '后端生产化封装 -- SQLite + WebSocket', detail: '创始人要求支持 2000-3000+ 并发，但同时强调"Keep it simple"。技术方案第一版过度设计，被否决。简化为 SQLite + SQLAlchemy 数据持久化、WebSocket 实时推送。16个 API 测试通过。' },
      { num: 5, date: '1/29', title: '测试 + API 文档 + 前端 HTML -> Next.js 迁移', detail: '完整 API 测试跑通，生成 API 文档。开始将 HTML 首页和文章详情页迁移到 Next.js 14（App Router），采用 CSS Modules + CSS Variables。' },
      { num: 6, date: '1/30', title: 'Experience 页面 + SecondMe 数据集成研究', detail: '并行开发体验页面：SecondMe OAuth2 登录、需求提交、实时协商展示。研究 SecondMe API 数据结构以减少用户手动输入。创始人要求"直接并行启动然后一直开发"。' },
      { num: 7, date: '1/30', title: '首页内容填充 + 文章系统 + 屏幕比例修复', detail: '修复屏幕比例（body 字体 19px -> 16px）和响应式布局。首页 Hero 标题定为"为 Agent 重新设计的互联网"。创建文章列表页，填入3篇完整文章。创始人指出"协议的价值应该来自创造，而不是采用"。' },
      { num: 8, date: '1/30', title: '文章内容 + 暖色调设计 + 滚动渐变背景', detail: '填入"道生一"和"微小的光"文章。创始人觉得网站太冷/临床感——"背后的网格给人更多囚禁的秩序感"。移除网格线，添加滚动渐变背景。从 #EEEEEE 冷灰到 #F8F6F3 暖米白。' },
      { num: 9, date: '1/30', title: 'OAuth 修复 + 实时协商 + 打字机效果 + Vercel 部署', detail: '修复 OAuth 回调不跳转问题（返回 JSON 而非重定向），实现需求提交和实时协商展示。添加流式消息的打字机效果改善 UX。代码审查发现硬编码密码哈希，移至环境变量。部署到 Vercel + CDN。' },
      { num: 10, date: '1/30', title: 'Redis Session + beads 任务管理 + UI 更新', detail: '创建 Redis Session 存储迁移文档和4个实现文件。UI 微调：把"加入网络"改为"体验 Demo"，更新联系邮箱，添加微信群二维码，移除尚未准备好的 GitHub 和 Twitter 链接。' },
      { num: 11, date: '1/30', title: '"一键体验" + "找技术合伙人"演示场景设计', detail: '实现一键体验功能。创始人否决了"独立音乐人演出"场景。改为"找技术合伙人"——展示"认知转变"：用户以为需要"技术合伙人"，发现真正需要的是"快速验证需求的能力"。设计了7个 Agent 和6个协商阶段。' },
      { num: 12, date: '1/30', title: 'WebSocket 跨域修复 + Experience UI 优化 + Vercel 绑定', detail: 'WebSocket 因 Cookie samesite="lax" 不跨域发送。添加 /ws/demo/ 无认证端点 + 前端自动检测跨域。用户信息移至右上角固定位置，添加可折叠 Profile 卡片。绑定 Vercel 到 GitHub 自动部署。' },
      { num: 13, date: '1/30', title: 'SecondMe 数据扩展 + 移动端适配 + 滚动渐变修复', detail: '创始人说"SecondMe那里获得的基本信息太少了"——添加 selfIntroduction、profileCompleteness 等新字段。修复背景渐变为 fixed 定位。全站移动端响应式适配（17个文件，1134行）。' },
      { num: 14, date: '1/30', title: 'Demo V2 -- 10 阶段完整交互动画', detail: '创始人详细描述了完整的交互流程：需求缩小为点、射出线条、背景圆圈闪烁广播、Agent 发现和分类、绿色 Agent 汇聚、响应展示、信息汇聚中心、筛选与点对点协商、最终提案。实现了10阶段的状态机动画。' },
      { num: 15, date: '1/31', title: 'Railway 部署 + 多环境 OAuth + Experience V3（真实 Agent）', detail: 'Railway 后端部署 + Vercel 前端部署。支持本地和生产 OAuth 回调。创建 experience-v3 使用真实 OpenAgents 数据，保留 experience-v2 演示版本。' },
      { num: 16, date: '1/31', title: 'WebSocket 断连排查 + React StrictMode 双挂载', detail: 'WebSocket 连接后立即断开——发现是 React Strict Mode 导致的双挂载/卸载。开发环境特有的问题，生产不受影响。研究 OpenAgents 网络为何之前能用现在不行。' },
      { num: 17, date: '2/4', title: '招募文章 + Hero 调整 + 架构反思的开端', detail: '添加招募共创文章，修改 Hero 区域。转折点：创始人表达了对架构的根本性担忧——"设计得很理想，但架构就是出很多小错误"。提供三篇核心文档，要求"你先去看这三个文档，然后我们再讨论技术架构本身"。从"做"转向了"想"。' },
      { num: 18, date: '2/5', title: '读三篇文档 + "不要为了 MVP 而 MVP"', detail: '读白皮书、技术简报、设计日志。创始人强调"不要为了做MVP而做MVP，不要为了单纯的削减功能而用削减功能"——最小完整单元不等于砍功能，原子必须本身完整、可递归。' },
      { num: 19, date: '2/5', title: '继续读文档 + 准备深入架构讨论', detail: '继续消化三篇核心文档，整理技术概念和架构决策记录。为接下来的深度讨论做准备。这是"慢下来"的必要成本。' },
    ],
  },
  {
    label: '会话 2',
    dateRange: '黑客松工具链 / 2/7',
    color: '#C47030',
    compacts: [
      { num: 20, date: '2/7', title: '黑客松工具链启动 -- Guide + Team Matcher + towow-dev Skill', detail: '启动通爻黑客松工具链开发。用 arch skill 方法论先思考每个交付物的本质——Guide 不是教程而是"认知透镜"，Team Matcher 不是匹配工具而是"协作可能性发现引擎"。使用 Opus 4.6 并行 Agent 开发。' },
      { num: 21, date: '2/7', title: 'Team Matcher 后端 + 前端并行开发', detail: '并行开发 Team Matcher 的后端 API、组队引擎和前端 UI。创始人明确要求用 Opus 4.6 而非 Sonnet 4.5。实现了路由从 /team 到 /apps/team-matcher 的重构，建立了前后端并行开发的任务依赖。' },
      { num: 22, date: '2/7', title: 'SecondMe Chat API 集成设计', detail: '进入 Plan Mode 设计 SecondMe Chat API 集成策略。创始人提供完整 API 文档。这是从"用户手动输入"到"AI 辅助填写"的升级——登录后 AI 基于 Profile 建议表单内容。' },
      { num: 23, date: '2/7', title: 'SecondMe Chat API 实现 + 组队引擎 LLM 集成', detail: '实现 SSE 流式调用 SecondMe Chat API。创建 team_prompts.py 包含 LLM 组队建议的 system/user prompt、JSON 提取和标准化。' },
      { num: 24, date: '2/7', title: 'Wave 2 并行开发 + 5 个集成 Bug 修复', detail: 'Opus 4.6 Agent 并行修改组队引擎和 WebSocket streaming。代码验收发现5个关键集成 Bug：WebSocket 消息被丢弃、Channel ID 不匹配、字段名不一致、API URL 路径错误、access_token 未持久化。全部修复。' },
      { num: 25, date: '2/7', title: '"不要模拟，直接变成应用" -- 用户爆发', detail: '应用停在"广播中..."无反应，测试通过但实际不工作——mock 数据掩盖了真实的集成失败。创始人深度挫败："mock模式不重要，直接变成应用"、"不要说什么模拟五个Agent去响应"。' },
      { num: 26, date: '2/7', title: 'UX 改进 + 技能标签扩展 + SecondMe 自动填表构想', detail: '进度页从"正在广播..."到有实际信息展示。技能标签扩展（加入 AI 原生、非技术类标签）。构想 SecondMe 自动填表：登录后 AI 基于 Profile 建议表单值。' },
      { num: 27, date: '2/7', title: 'SecondMe 自动填表实现 + Plan Mode', detail: '实现 SecondMe auto-fill：登录后调用 Chat API，基于 Profile + 黑客松上下文建议表单值。打字机效果逐字填入——UX 细节让自动化过程可感知而非突然出现。' },
    ],
  },
  {
    label: '会话 3',
    dateRange: '架构设计 + 共建体系 / 2/6 - 2/8',
    color: '#5A8A64',
    compacts: [
      { num: 28, date: '2/6', title: '签名广播机制设计 -- HDC + 三层共振过滤', detail: '设计信号共振机制：Bloom Filter（90%过滤，100ns/检测）、HDC 共振检测（9%过滤，1us）、LLM 深度理解（1%处理，10ms）。超维计算核心：10,000维二进制超向量，SimHash 编码保留语义。创始人关键洞察："广播和筛选是同一个逻辑执行了两次"。' },
      { num: 29, date: '2/6', title: 'Agent 接入机制 + Skill 系统设计', detail: '讨论 Agent 如何接入网络。创始人提出"Agent 就是你的 Profile"——用户不需要"构建 Agent"，只需提供信息。Skill 系统研究了20+篇论文，发现多轮辩论净负面（-3.5%），但并行提案到聚合正面（+57-81%）。' },
      { num: 30, date: '2/6', title: '架构全面审视 -- 自洽性 + 白皮书对齐', detail: '全面审查已完成架构章节的内部一致性。对照白皮书交叉验证。检查是否满足"美"、"极简"和"最小完整单元"原则。这一轮是"元审视"——不是写新内容，而是检查已有内容是否自洽。' },
      { num: 31, date: '2/6', title: 'Offer 沉淀 -> Service Agent 结晶 + 设计原则提取', detail: '深入讨论 Offer 如何沉淀为 Service Agent 的结晶模型。提取新的设计原则——"需求 != 要求"（需求是抽象的张力，要求是具象的假设性解法）。确保工程服务于商业目标。' },
      { num: 32, date: '2/6', title: '元审视 -- "一个问题解锁所有问题" + 价值信号', detail: '架构元审视：盲点、自洽性、商业与工程对齐。创始人问"那一个能解锁所有问题的问题是什么？" 答案浮现：价值信号/反馈闭环——系统怎么知道自己在 work？波浪出去了，但没有回来。这是"管道，不是场"。' },
      { num: 33, date: '2/6', title: 'WOWOK 区块链协议集成 -- "波浪回来"', detail: '创始人纠正了方法："你只是给我执行了，但你没有想清楚，没去思考。" 应该先讨论确认理解，再写文档。深入理解 WOWOK 协议（Machine/Progress = 本质 vs 实现，Service/Order = 本质 vs 实现，Guard = 验证引擎不是签名本身）。' },
      { num: 34, date: '2/6', title: 'WOWOK 核心概念 + 共振阈值 k* 机制', detail: '确认 WOWOK 9个核心对象理解。设计共振阈值策略：k* 不是预设常数，而是从期望响应数计算出来的。一个 k* 规则统一解决了初始值设定、通过率期望、场景差异、自适应调整和冷启动5个问题。' },
      { num: 35, date: '2/6', title: '"投影即函数" -- 架构本质的顿悟', detail: '讨论 Service Agent 结晶机制时，方案变得过度复杂。创始人质疑："本质和实现没有区分开来，不应该这么复杂。" 多次思维跳跃后确立核心原则：Agent = 投影函数的结果，不是有状态对象。Profile Data 住在数据源，通爻只投影。一个概念消除了四个问题。' },
      { num: 36, date: '2/7', title: 'A2A 黑客松策略 -- 工具链设计思考', detail: '为 A2A 黑客松设计工具链。用 arch skill 方法论思考每个交付物——不是"做出来"而是"做对"。Guide = 认知透镜，Team Matcher = 协作可能性发现引擎，towow-dev skill = 工程领导者角色。' },
      { num: 37, date: '2/7', title: '架构文档全面更新 -- Design Log 回填', detail: '创始人明确"我们还没有开始做实现，我们单纯在做架构"。将 Design Log #001/#002/#003 的洞察回填到 ARCHITECTURE_DESIGN.md。不触碰实现代码——这是刻意的。' },
      { num: 38, date: '2/8', title: 'Task/PRD Skill 创建 + 33->18 任务精简', detail: '创始人要求创建专门的 PRD Skill。用 arch skill 重新评估33个任务。创始人多次纠正评估方向——"不是为了有任务而有任务"。最终精简为18个：不是因为数量太多，而是有些任务的"本质问题"不够真实。' },
      { num: 39, date: '2/8', title: '9 个 Agent 并行写 18 篇 PRD', detail: '创始人纠正了我对架构设计承诺的误解。然后启动9个 Opus 4.6 Agent 并行编写全部18篇 PRD，每个 Agent 使用 arch + task-arch skill。这是"投影"的一个实例——同一个架构文档，通过9个不同的 Agent 透镜，产生18篇各有特点的 PRD。' },
      { num: 40, date: '2/8', title: '交付规划 -- 飞书 + 网站 /contribute 页面', detail: '9个 Agent 完成18篇 PRD。创始人决策：飞书为主（Bitable + 手动粘贴管理），网站为辅（build in public）。创建 /contribute 页面第一版、Feishu CSV 导入文件。' },
      { num: 41, date: '2/8', title: '/contribute 三次迭代 + 飞书群公告 + 部署上线', detail: '/contribute 页面三次迭代：太花哨 -> 太简洁 -> "不是为了简洁而简洁"。添加字段标签、目标描述、"任务1/2/3"编号。创建飞书群公告文档。一次提交165文件，+18,795行。部署上线，开放共建基础设施完成。' },
    ],
  },
];

// --- Component ---

export default function JourneyPage() {
  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(new Set());
  const [expandedCompacts, setExpandedCompacts] = useState<Set<number>>(new Set());

  const togglePhase = useCallback((num: number) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num);
      else next.add(num);
      return next;
    });
  }, []);

  const toggleCompact = useCallback((num: number) => {
    setExpandedCompacts((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num);
      else next.add(num);
      return next;
    });
  }, []);

  // Cmd+E to expand/collapse all compacts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'e' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setExpandedCompacts((prev) => {
          const allNums = SESSIONS.flatMap((s) => s.compacts.map((c) => c.num));
          if (prev.size === allNums.length) return new Set();
          return new Set(allNums);
        });
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className={styles.page}>
      {/* Layer 0: Title + Stats */}
      <header className={styles.header}>
        <h1 className={styles.title}>19天，3次蜕变，从代码到道</h1>
        <p className={styles.subtitle}>
          一个人和一个AI，从零搭建了一个协议的完整架构、网站、工具链和共建体系。不是写代码的故事，是找到"道"的故事。
        </p>
      </header>

      <div className={styles.statsBar}>
        {STATS.map((s) => (
          <div key={s.label} className={styles.statCard}>
            <div className={styles.statNum}>{s.num}</div>
            <div className={styles.statLabel}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Layer 1: Three Transformations */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <span className={styles.dot} style={{ background: '#C47030' }} />
          三个转变
        </h2>
        <div className={styles.transformGrid}>
          {TRANSFORMATIONS.map((t) => (
            <div key={t.label} className={styles.transformCard}>
              <div className={styles.transformTime}>{t.time}</div>
              <h3 className={styles.transformLabel}>{t.label}</h3>
              <p className={styles.transformOneLiner}>{t.oneLiner}</p>
              <p className={styles.transformMeaning}>
                <span className={styles.fieldLabel}>意味着</span>
                {t.meaning}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Phase Flow */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <span className={styles.dot} style={{ background: '#F9A87C' }} />
          开发阶段
        </h2>
        <div className={styles.flow}>
          {PHASES.map((p, i) => (
            <span key={p.num}>
              <span
                className={styles.flowNode}
                style={{
                  background:
                    i < 2
                      ? 'rgba(139,106,144,0.12)'
                      : i < 4
                        ? 'rgba(196,112,48,0.1)'
                        : 'rgba(90,138,100,0.1)',
                  color: i < 2 ? '#8B6A90' : i < 4 ? '#C47030' : '#5A8A64',
                }}
              >
                {p.name}
              </span>
              {i < PHASES.length - 1 && (
                <span className={styles.flowArrow}>&#8594;</span>
              )}
            </span>
          ))}
        </div>
      </section>

      {/* Layer 2: Phases */}
      <section className={styles.section}>
        <div className={styles.phaseGrid}>
          {PHASES.map((p) => {
            const isOpen = expandedPhases.has(p.num);
            return (
              <div
                key={p.num}
                className={`${styles.phaseCard} ${p.num === 7 ? styles.phaseCardFull : ''}`}
                onClick={() => togglePhase(p.num)}
              >
                <div className={styles.phaseTop}>
                  <span className={styles.phaseNum}>阶段 {p.num}</span>
                  <span className={styles.phaseDates}>{p.dates}</span>
                </div>
                <h3 className={styles.phaseName}>{p.name}</h3>
                <p className={styles.phaseNarrative}>{p.narrative}</p>
                <div className={styles.phaseTags}>
                  {p.tags.map((tag) => (
                    <span
                      key={tag.label}
                      className={`${styles.tag} ${styles[`tag${tag.color.charAt(0).toUpperCase() + tag.color.slice(1)}`]}`}
                    >
                      {tag.label}
                    </span>
                  ))}
                </div>
                <div className={styles.phaseStats}>{p.stats}</div>

                {isOpen && (
                  <div className={styles.phaseDetail}>
                    {p.decisions.length > 0 && (
                      <div className={styles.detailBlock}>
                        <span className={styles.fieldLabel}>关键决策</span>
                        <ul className={styles.detailList}>
                          {p.decisions.map((d, i) => (
                            <li key={i}>{d}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {p.corrections.length > 0 && (
                      <div className={styles.detailBlock}>
                        <span className={styles.fieldLabel}>用户纠正</span>
                        <ul className={styles.detailList}>
                          {p.corrections.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {p.surprise && (
                      <div className={styles.detailBlock}>
                        <span className={styles.fieldLabel}>意外发现</span>
                        <p className={styles.detailText}>{p.surprise}</p>
                      </div>
                    )}
                    {p.quote && (
                      <blockquote className={styles.quoteBox}>
                        <p>"{p.quote}"</p>
                        {p.quoteAuthor && (
                          <cite>-- {p.quoteAuthor}</cite>
                        )}
                      </blockquote>
                    )}
                  </div>
                )}

                <div className={styles.expandHint}>
                  {isOpen ? '收起' : '展开详情'}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Layer 3: Compact List */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <span className={styles.dot} style={{ background: '#5A8A64' }} />
          41 次上下文压缩 -- 工作脉络
        </h2>
        <p className={styles.sectionSubtitle}>
          每次压缩代表一轮深入的对话+开发周期（约 200K tokens）。点击展开详情。
          <span className={styles.shortcutHint}>Cmd+E 展开/折叠全部</span>
        </p>

        {SESSIONS.map((session) => (
          <div key={session.label} className={styles.sessionGroup}>
            <div
              className={styles.sessionLabel}
              style={{ color: session.color }}
            >
              {session.label} / {session.dateRange}
            </div>
            <div className={styles.compactList}>
              {session.compacts.map((c) => {
                const isOpen = expandedCompacts.has(c.num);
                return (
                  <div
                    key={c.num}
                    className={`${styles.compactItem} ${isOpen ? styles.compactOpen : ''}`}
                    onClick={() => toggleCompact(c.num)}
                  >
                    <div
                      className={styles.compactNum}
                      style={{ color: session.color }}
                    >
                      {c.num}
                    </div>
                    <div className={styles.compactContent}>
                      <div className={styles.compactTitle}>{c.title}</div>
                      <div className={styles.compactMeta}>{c.date}</div>
                      {isOpen && (
                        <div className={styles.compactDetail}>{c.detail}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </section>

      {/* Layer 4: Links */}
      <section className={styles.footer}>
        <h2 className={styles.footerTitle}>完整素材</h2>
        <p className={styles.footerText}>
          以上是19天工作历程的结构化叙述。更多原始素材和完整文档：
        </p>
        <ul className={styles.linkList}>
          <li>
            <a
              href="https://github.com/anthropics/towow/blob/main/raphael/docs/work_session_summaries.md"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.footerLink}
            >
              完整工作摘要（41条） &#8594;
            </a>
          </li>
          <li>
            <a
              href="https://github.com/anthropics/towow/blob/main/raphael/docs/ARCHITECTURE_DESIGN.md"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.footerLink}
            >
              架构设计文档 &#8594;
            </a>
          </li>
          <li>
            <a
              href="https://github.com/anthropics/towow/blob/main/raphael/docs/DESIGN_LOG_001_PROJECTION_AND_SELF.md"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.footerLink}
            >
              Design Log #001: 投影与自 &#8594;
            </a>
          </li>
        </ul>
      </section>
    </div>
  );
}
