// app/contribute/page.tsx
import Link from 'next/link';
import styles from './contribute.module.css';

export const metadata = {
  title: '共建任务 - ToWow 通爻',
  description: '通爻网络的共建任务看板。找到你感兴趣的任务，用你的方式参与建设。',
};

// --- Data ---

interface Task {
  name: string;
  oneLiner: string;
  target: string;
  tier: 1 | 2 | 'template';
  prdUrl: string;
}

interface Track {
  id: string;
  name: string;
  color: string;
  goal: string;
  dependency?: string;
  tasks: Task[];
}

const TRACKS: Track[] = [
  {
    id: 'core',
    name: '核心验证',
    color: '#D4B8D9',
    goal: '验证通爻的核心技术假设——HDC 编码、共振检测、协商引擎——在真实场景下效果有多好。',
    dependency: '实验设计 → 编码验证 → 可视化（顺序依赖）',
    tasks: [
      {
        name: '最小验证实验设计', tier: 1,
        oneLiner: '设计最小实验，量化通爻 5 个核心假设的实际效果。这是所有后续验证的起点。',
        target: '有实验设计能力的人（研究背景 / 数据科学）',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/H4_minimum_validation_experiments.md',
      },
      {
        name: 'HDC 编码策略验证', tier: 1,
        oneLiner: '对比不同编码方法，找到最优的"文本 → 超向量"编码策略。决定了系统的信号质量。',
        target: '懂 NLP / ML 的开发者或研究生',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/A1_hdc_encoding.md',
      },
      {
        name: '超向量空间可视化', tier: 2,
        oneLiner: '让人"看到"HDC 空间中 Agent 的分布和共振效果，验证编码是否符合直觉。',
        target: '有前端和数据可视化经验的开发者',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/H5_hypervector_visualization.md',
      },
    ],
  },
  {
    id: 'positioning',
    name: '定位与传播',
    color: '#D4F4DD',
    goal: '对外讲清楚通爻是什么、不是什么，让不同背景的人都能理解响应范式的价值。',
    dependency: '竞品对标 → 科普文章 → 技术博客（内容递进）；概念翻译、术语表、案例故事可独立启动',
    tasks: [
      {
        name: '竞品 / 参考系统对标分析', tier: 1,
        oneLiner: '系统分析通爻和 AutoGen、推荐系统、Fetch.ai 等的范式级差异，找到清晰的差异化定位。',
        target: '了解 AI Agent 生态的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/A5_competitive_analysis.md',
      },
      {
        name: '响应范式科普文章', tier: 1,
        oneLiner: '零技术门槛，3 分钟让人理解"搜索"和"响应"的根本区别。面向最广泛的受众。',
        target: '写作能力强的人（可以不懂技术）',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/D1_response_paradigm_article.md',
      },
      {
        name: '概念翻译（跨领域）', tier: 1,
        oneLiner: '让招聘、区块链、投资、产品领域的人用自己的语言理解通爻，扩展受众圈层。',
        target: '有跨领域背景的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/H1_concept_translation.md',
      },
      {
        name: '核心术语表（中英双语）', tier: 2,
        oneLiner: '30-40 个核心术语的中英对照，保留技术含义和哲学内涵。',
        target: '懂技术英文、理解哲学概念的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/C1_glossary.md',
      },
      {
        name: '"投影即函数"技术博客', tier: 2,
        oneLiner: '面向技术读者讲清楚核心洞察：Agent 是函数不是对象，投影是基本操作。',
        target: '有技术写作能力的开发者',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/D2_projection_as_function_blog.md',
      },
      {
        name: '从需求到发现：案例故事', tier: 2,
        oneLiner: '一个完整的故事，让人感受到响应范式发现意外价值的力量。',
        target: '有叙事能力的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/D5_demand_to_discovery_story.md',
      },
    ],
  },
  {
    id: 'product',
    name: '场景与产品',
    color: '#FFE4B5',
    goal: '把理念变成可用的应用。验证通爻协议在真实场景中能否创造价值。',
    dependency: '场景建模 → 场景模板 → 小应用模板（递进）；Prompt 工程独立路径',
    tasks: [
      {
        name: '黑客松组队场景建模', tier: 1,
        oneLiner: '系统化分析"找队友到组成团队"的完整用户旅程和决策因素。这是通爻的第一个落地场景。',
        target: '参加过黑客松的人 / 产品经理',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/B1_hackathon_teaming.md',
      },
      {
        name: 'Prompt 工程研究', tier: 1,
        oneLiner: '系统化优化通爻 6 个核心 Skill 的 LLM Prompt，提升协商质量。',
        target: '有 Prompt 工程经验的开发者',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/H2_prompt_engineering.md',
      },
      {
        name: '场景建模模板', tier: 'template',
        oneLiner: '为新领域的共建者提供场景建模的标准流程和模板。',
        target: '任何领域的人（招聘、餐饮、教育……）',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/T1_scene_modeling_template.md',
      },
      {
        name: '独立小应用模板', tier: 'template',
        oneLiner: '用通爻理念做实际产品的任务模板，帮助开发者快速启动。',
        target: '有开发能力的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/T2_indie_app_template.md',
      },
    ],
  },
  {
    id: 'frontier',
    name: '前沿探索',
    color: '#F9A87C',
    goal: '长期技术储备。这些方向暂时不影响 V1 开发，但对通爻网络的远期演化至关重要。',
    dependency: '四个方向互不依赖，按个人兴趣认领',
    tasks: [
      {
        name: '分布式共振网络学术调研', tier: 2,
        oneLiner: 'V1 用中心化广播，长期需要分布式。做一份学术综述作为知识储备。',
        target: '有学术研究能力的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/A2_distributed_resonance_survey.md',
      },
      {
        name: '经济激励模型方向探索', tier: 2,
        oneLiner: '网络需要激励机制让人参与，梳理可选方向和 trade-off。',
        target: '懂经济学 / 博弈论或 Token 设计的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/A3_economic_incentive_model.md',
      },
      {
        name: '安全模型与数据所有权调研', tier: 2,
        oneLiner: '通爻涉及个人数据和 Agent 行为，安全和隐私怎么保障。',
        target: '有安全 / 隐私研究背景的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/A4_security_data_ownership.md',
      },
      {
        name: 'Sui 链数据成本与性能实测', tier: 2,
        oneLiner: 'WOWOK 在 Sui 上实测链上操作的成本和性能，为链上执行层提供数据支撑。',
        target: '有 Sui / Move 开发经验的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/A6_sui_chain_benchmark.md',
      },
    ],
  },
  {
    id: 'ecosystem',
    name: '开发者生态',
    color: '#E8F3E8',
    goal: '让其他开发者能理解通爻并用它来做东西。降低接入门槛。',
    tasks: [
      {
        name: '开发者入门套件', tier: 1,
        oneLiner: '让开发者 30 分钟内理解通爻并开始构建自己的场景。',
        target: '有开发经验且理解通爻理念的人',
        prdUrl: 'https://github.com/anthropics/towow/blob/main/raphael/docs/tasks/H3_developer_starter_kit.md',
      },
    ],
  },
];

// --- Helpers ---

function tierLabel(tier: 1 | 2 | 'template') {
  if (tier === 1) return '优先';
  if (tier === 2) return '探索';
  return '模板';
}

// --- Page ---

export default function ContributePage() {
  const totalTasks = TRACKS.reduce((sum, t) => sum + t.tasks.length, 0);
  const tier1Count = TRACKS.reduce(
    (sum, t) => sum + t.tasks.filter(task => task.tier === 1).length, 0
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>共建任务</h1>
        <p className={styles.subtitle}>
          通爻网络的开放任务看板。当前 {totalTasks} 个任务，其中 {tier1Count} 个优先。
          找到你感兴趣的方向，点击查看详细 PRD，用你的方式参与建设。
        </p>
      </header>

      {TRACKS.map((track) => (
        <section key={track.id} className={styles.track}>
          <div className={styles.trackHead}>
            <div className={styles.trackLabelRow}>
              <span className={styles.trackDot} style={{ background: track.color }} />
              <span className={styles.trackLabel}>主线</span>
            </div>
            <h2 className={styles.trackName}>{track.name}</h2>
            <div className={styles.trackMeta}>
              <p className={styles.trackMetaRow}>
                <span className={styles.fieldLabel}>目标</span>
                {track.goal}
              </p>
              {track.dependency && (
                <p className={styles.trackMetaRow}>
                  <span className={styles.fieldLabel}>依赖</span>
                  {track.dependency}
                </p>
              )}
            </div>
          </div>

          <div className={styles.taskGrid}>
            {track.tasks.map((task, index) => (
              <a
                key={index}
                href={task.prdUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.taskCard}
              >
                <div className={styles.cardTop}>
                  <span className={styles.taskNum}>任务 {index + 1}</span>
                  <span className={`${styles.tier} ${
                    task.tier === 1 ? styles.tier1
                      : task.tier === 2 ? styles.tier2
                      : styles.tierTpl
                  }`}>
                    {tierLabel(task.tier)}
                  </span>
                </div>
                <h3 className={styles.taskName}>{task.name}</h3>
                <p className={styles.taskDesc}>{task.oneLiner}</p>
                <p className={styles.taskTarget}>
                  <span className={styles.fieldLabel}>适合</span>
                  {task.target}
                </p>
              </a>
            ))}
          </div>
        </section>
      ))}

      <section className={styles.howTo}>
        <h2 className={styles.howToTitle}>怎么参与</h2>
        <p className={styles.howToText}>
          浏览上面的任务，找到匹配你背景和兴趣的方向。点击任务卡片可以查看详细的
          PRD 文档，包含背景、目标、子任务拆解和验收标准。准备好了就在飞书群里认领。
          我们也欢迎你提出新的任务方向——有什么人就做什么事。
        </p>
        <Link href="/articles/join-us" className={styles.ctaLink}>
          加入共创 →
        </Link>
      </section>
    </div>
  );
}
