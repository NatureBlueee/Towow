/**
 * 通爻应用注册表
 *
 * 所有应用的元数据都在这里统一管理
 * 添加新应用只需在这里注册即可
 */

import { AppMetadata } from './types';

export const APPS: AppMetadata[] = [
  // ============================================
  // 活跃应用（Active Apps）
  // ============================================

  {
    id: 'team-matcher',
    name: 'Team Matcher',
    nameZh: '组队匹配',
    description: 'Hackathon team matching powered by response paradigm',
    descriptionZh: '黑客松组队匹配 - 响应范式的全新组队体验',
    icon: '🤝',
    path: '/apps/team-matcher/request',
    status: 'active',
    category: 'matching',
    tags: ['黑客松', '组队', '响应范式', 'Dark Glassmorphism'],
    featured: true,
    preview: {
      image: '/team-matcher-preview.png',
      screenshots: [
        '/team-request-page.png',
        '/team-progress-broadcasting.png',
        '/team-proposals-page.png',
      ],
    },
    author: 'ToWow Team',
    version: '1.0.0',
    createdAt: '2026-02-07',
  },

  {
    id: 'demand-negotiation',
    name: 'Demand Negotiation',
    nameZh: '需求协商',
    description: 'Multi-agent negotiation demo',
    descriptionZh: '多 Agent 需求协商演示 - 体验 AI Agent 如何协作',
    icon: '💬',
    path: '/apps/demand-negotiation',
    status: 'active',
    category: 'negotiation',
    tags: ['需求', '协商', 'Agent', '演示'],
    featured: false,
    author: 'ToWow Team',
    version: '2.0.0',
    createdAt: '2026-01-30',
  },

  // ============================================
  // Beta 测试应用（Beta Apps）
  // ============================================

  // 暂无

  // ============================================
  // 即将推出（Coming Soon）
  // ============================================

  {
    id: 'skill-exchange',
    name: 'Skill Exchange',
    nameZh: '技能交换',
    description: 'Peer-to-peer skill sharing network',
    descriptionZh: '点对点技能交换平台 - 互助学习网络',
    icon: '📚',
    path: '/apps/skill-exchange',
    status: 'coming-soon',
    category: 'exchange',
    tags: ['技能', '学习', '互助', '点对点'],
    featured: false,
  },

  {
    id: 'project-collaboration',
    name: 'Project Collaboration',
    nameZh: '项目协作',
    description: 'Decentralized project collaboration',
    descriptionZh: '去中心化项目协作 - 无需项目管理的协作方式',
    icon: '🎯',
    path: '/apps/project-collaboration',
    status: 'coming-soon',
    category: 'collaboration',
    tags: ['项目', '协作', '去中心化'],
    featured: false,
  },

  {
    id: 'resource-matching',
    name: 'Resource Matching',
    nameZh: '资源匹配',
    description: 'Match resources and needs automatically',
    descriptionZh: '资源与需求自动匹配 - 让供需自然相遇',
    icon: '🔄',
    path: '/apps/resource-matching',
    status: 'coming-soon',
    category: 'matching',
    tags: ['资源', '需求', '匹配'],
    featured: false,
  },
];

// ============================================
// 辅助函数（Helper Functions）
// ============================================

/**
 * 获取所有活跃应用
 */
export function getActiveApps(): AppMetadata[] {
  return APPS.filter(app => app.status === 'active');
}

/**
 * 获取推荐应用
 */
export function getFeaturedApps(): AppMetadata[] {
  return APPS.filter(app => app.featured && app.status === 'active');
}

/**
 * 根据分类获取应用
 */
export function getAppsByCategory(category: string): AppMetadata[] {
  return APPS.filter(app => app.category === category);
}

/**
 * 根据 ID 获取应用
 */
export function getAppById(id: string): AppMetadata | undefined {
  return APPS.find(app => app.id === id);
}

/**
 * 获取即将推出的应用
 */
export function getComingSoonApps(): AppMetadata[] {
  return APPS.filter(app => app.status === 'coming-soon');
}

/**
 * 搜索应用（按名称或标签）
 */
export function searchApps(query: string): AppMetadata[] {
  const lowerQuery = query.toLowerCase();
  return APPS.filter(app =>
    app.name.toLowerCase().includes(lowerQuery) ||
    app.nameZh?.toLowerCase().includes(lowerQuery) ||
    app.description.toLowerCase().includes(lowerQuery) ||
    app.descriptionZh?.toLowerCase().includes(lowerQuery) ||
    app.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
  );
}
