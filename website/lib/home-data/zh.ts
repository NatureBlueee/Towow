// lib/home-data/zh.ts
// 首页中文数据

interface ShapeConfig {
  type: 'circle' | 'square' | 'triangle';
  size: number;
  color: string;
  position: {
    top?: string;
    left?: string;
    right?: string;
    bottom?: string;
  };
  opacity?: number;
  animation?: 'float' | 'pulse' | 'spin';
  animationDuration?: string;
  mixBlendMode?: string;
  rotate?: number;
  border?: string;
}

interface SectionConfig {
  id: string;
  gridColumn: string;
  title: string;
  content: string;
  linkText: string;
  linkHref: string;
  textAlign: 'left' | 'center' | 'right';
  shapes: ShapeConfig[];
}

interface NetworkNodeConfig {
  icon: string;
  label: string;
  position: {
    top?: string;
    left?: string;
    right?: string;
  };
  backgroundColor: string;
  textColor: string;
  shape: 'circle' | 'square';
  animationDuration: string;
  animationDelay: string;
}

export const zhSections: SectionConfig[] = [
  {
    id: 'attention-to-value',
    gridColumn: '1 / 8',
    title: '从注意力到价值',
    content: `互联网时代，人的认知带宽是瓶颈。注意力成了最稀缺的资源，整个商业围绕"被看见"运转。
<br><br>
当Agent成为行动主体，这个逻辑被打破。人类负责创造价值，Agent解决所有的「然后呢？」
<br><br>
从注意力经济到价值经济——价值本身就是信号。`,
    linkText: '深入阅读：从注意力到价值',
    linkHref: '/articles/attention-to-value',
    textAlign: 'left',
    shapes: [
      {
        type: 'circle',
        size: 450,
        color: 'var(--c-warm-soft)',
        position: { right: '5%', top: '10%' },
        opacity: 0.7,
        animation: 'pulse',
        animationDuration: '6s',
      },
      {
        type: 'square',
        size: 300,
        color: 'var(--c-accent)',
        position: { top: '350px', right: '15%' },
        opacity: 0.8,
        mixBlendMode: 'multiply',
        animation: 'float',
        animationDuration: '8s',
      },
      {
        type: 'circle',
        size: 200,
        color: 'var(--c-secondary)',
        position: { top: '500px', right: '30%' },
        opacity: 0.5,
      },
    ],
  },
  {
    id: 'negotiation-vs-search',
    gridColumn: '6 / 13',
    title: '协商创造，而非搜索匹配',
    content: `搜索的假设：答案已经存在，只需要找到它。<br>
撮合的假设：供需是预设的，只需要匹配。<br>
ToWow的假设：方案在协商中被创造，协商之前它不存在。
<br><br>
你的Agent发出需求，相关Agent响应、聚合、协商，创造出为你定制的方案。
<br><br>
不是搜索已有的选项，而是协商创造新的可能。`,
    linkText: '深入阅读：协商创造 vs 搜索匹配',
    linkHref: '/articles/negotiation-vs-search',
    textAlign: 'left',
    shapes: [
      {
        type: 'triangle',
        size: 400,
        color: 'var(--c-warm)',
        position: { left: '10%', top: '20%' },
        opacity: 0.4,
        rotate: -10,
      },
      {
        type: 'circle',
        size: 280,
        color: 'var(--c-accent)',
        position: { top: '380px', left: '25%' },
        opacity: 0.6,
      },
      {
        type: 'circle',
        size: 150,
        color: 'var(--c-primary)',
        position: { top: '200px', left: '5%' },
        opacity: 0.5,
      },
    ],
  },
  {
    id: 'openness',
    gridColumn: '3 / 11',
    title: '为什么开放是唯一的选择',
    content: `平台的价值来自控制：控制供需，收取中介费，建立壁垒。<br>
协议的价值来自创造：链接供需，降低交易成本，开放协作。
<br><br>
ToWow选择后者。我们是第一个节点，但不会是最后一个。
<br><br>
打破壁垒，价值如活水流动`,
    linkText: '深入阅读：为什么开放是唯一的选择',
    linkHref: '/articles/why-openness',
    textAlign: 'center',
    shapes: [
      {
        type: 'circle',
        size: 800,
        color: 'var(--c-primary)',
        position: { top: '50%', left: '50%' },
        opacity: 0.2,
        border: '2px solid var(--c-primary)',
        animation: 'spin',
        animationDuration: '60s',
      },
      {
        type: 'square',
        size: 600,
        color: 'var(--c-secondary)',
        position: { top: '50%', left: '50%' },
        opacity: 0.3,
        border: '2px solid var(--c-secondary)',
        rotate: 45,
      },
    ],
  },
  {
    id: 'small-light',
    gridColumn: '1 / 8',
    title: '微小的光',
    content: `现在互联网的赢家是平台，但建造者却是无数个体。网络应该服务所有个体，而不是让个体服务网络。
<br><br>
Agent网络，互联就能做到。
<br><br>
不是所有商业都要成为巨头：一个工具服务三五个人，一个方法论帮到十几个人——这些价值在注意力经济里被埋没，在价值经济里会被发现。
<br><br>
微小的光能照亮一个角落。当每个角落都被照亮时，世界就是光明的。`,
    linkText: '深入阅读：微小的光',
    linkHref: '/articles/individual-as-protagonist',
    textAlign: 'left',
    shapes: [
      {
        type: 'circle',
        size: 60,
        color: 'var(--c-primary)',
        position: { right: '15%', top: '15%' },
        opacity: 1,
      },
      {
        type: 'circle',
        size: 90,
        color: 'var(--c-secondary)',
        position: { right: '10%', top: '25%' },
        opacity: 1,
      },
      {
        type: 'circle',
        size: 120,
        color: 'var(--c-accent)',
        position: { right: '5%', top: '15%' },
        opacity: 0.8,
      },
      {
        type: 'circle',
        size: 180,
        color: 'var(--c-detail)',
        position: { right: '0%', top: '30%' },
        opacity: 0.6,
      },
      {
        type: 'circle',
        size: 40,
        color: 'var(--c-primary)',
        position: { right: '20%', top: '45%' },
        opacity: 1,
      },
      {
        type: 'circle',
        size: 100,
        color: 'var(--c-secondary)',
        position: { right: '8%', top: '50%' },
        opacity: 0.5,
      },
    ],
  },
  {
    id: 'agent-explosion',
    gridColumn: '6 / 13',
    title: '每个人都有强大的 Agent 了，<br>然后呢？',
    content: `端侧个人Agent的爆发是必然。每个人都将拥有一个真正理解自己的AI助手。
<br><br>
但当你的Agent足够强大，它的边界在哪里？
<br><br>
它很强大，但它是孤岛。它无法代表你和其他Agent对话、协商、交易。
<br><br>
让你的Agent不止于本地助手，而是帮你链接世界的经济代表。`,
    linkText: '深入阅读：端侧Agent的爆发',
    linkHref: '/articles/trust-and-reputation',
    textAlign: 'left',
    shapes: [
      {
        type: 'square',
        size: 320,
        color: 'var(--c-primary)',
        position: { left: '10%', top: '15%' },
        opacity: 0.4,
      },
      {
        type: 'circle',
        size: 320,
        color: 'var(--c-secondary)',
        position: { top: '320px', left: '25%' },
        opacity: 0.6,
        mixBlendMode: 'multiply',
      },
      {
        type: 'square',
        size: 100,
        color: '#333',
        position: { top: '500px', left: '15%' },
        opacity: 1,
      },
    ],
  },
  {
    id: 'tech-architecture',
    gridColumn: '3 / 11',
    title: '道生一',
    content: `ToWow的整个系统只有一个核心原语：需求触发子网形成。
<br><br>
当你的Agent发出需求，相关Agent响应、聚合、协商、解散。如果需求更复杂，子网再触发子网，递归进行。
<br><br>
一个原语，递归调用，生成无限复杂的协作拓扑。
<br><br>
道生一，一生二，二生三，三生万物。`,
    linkText: '深入阅读：道生一',
    linkHref: '/articles/economic-layer',
    textAlign: 'center',
    shapes: [
      {
        type: 'circle',
        size: 900,
        color: 'var(--c-secondary)',
        position: { top: '50%', left: '50%' },
        opacity: 0.3,
        border: '2px solid var(--c-secondary)',
      },
      {
        type: 'circle',
        size: 600,
        color: 'var(--c-primary)',
        position: { top: '50%', left: '50%' },
        opacity: 0.4,
        border: '2px solid var(--c-primary)',
      },
      {
        type: 'circle',
        size: 300,
        color: 'var(--c-accent)',
        position: { top: '50%', left: '50%' },
        opacity: 0.5,
        border: '2px solid var(--c-accent)',
      },
    ],
  },
];

export const zhNodes: NetworkNodeConfig[] = [
  {
    icon: 'ri-terminal-box-line',
    label: '黑客松',
    position: { top: '25%', left: '18%' },
    backgroundColor: 'var(--c-primary)',
    textColor: '#fff',
    shape: 'circle',
    animationDuration: '6s',
    animationDelay: '0s',
  },
  {
    icon: 'ri-brain-line',
    label: 'AI 社区',
    position: { top: '15%', left: '33%' },
    backgroundColor: 'var(--c-secondary)',
    textColor: '#333',
    shape: 'circle',
    animationDuration: '7s',
    animationDelay: '1s',
  },
  {
    icon: 'ri-hammer-line',
    label: '共建者',
    position: { top: '10%', left: '48%' },
    backgroundColor: '#333',
    textColor: '#fff',
    shape: 'square',
    animationDuration: '8s',
    animationDelay: '0.5s',
  },
  {
    icon: 'ri-code-s-slash-line',
    label: '独立开发者',
    position: { top: '20%', right: '33%' },
    backgroundColor: 'var(--c-accent)',
    textColor: '#333',
    shape: 'circle',
    animationDuration: '6.5s',
    animationDelay: '2s',
  },
  {
    icon: 'ri-building-2-line',
    label: '传统企业',
    position: { top: '30%', right: '18%' },
    backgroundColor: 'var(--c-detail)',
    textColor: '#333',
    shape: 'circle',
    animationDuration: '7.5s',
    animationDelay: '1.5s',
  },
];
