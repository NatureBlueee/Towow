/**
 * Store scene configuration.
 *
 * Each scene defines theme colors, hero copy, input placeholder/chips,
 * and center context for the negotiation engine.
 */

export interface SceneConfig {
  id: string;
  name: string;
  primary: string;
  accent: string;
  bg: string;
  hero: string;
  heroDesc: string;
  placeholder: string;
  chips: string[];
  centerContext: string;
  cardTemplate: 'hackathon' | 'default';
  planTemplate: 'team' | 'default';
}

export const SCENES: Record<string, SceneConfig> = {
  hackathon: {
    id: 'hackathon',
    name: '黑客松组队',
    primary: '#F9A87C',
    accent: '#E88A5C',
    bg: '#FFF8F0',
    hero: '48小时，你需要什么队友？',
    heroDesc: '描述你的项目方向和技能缺口，通爻网络中的开发者、设计师、产品经理会通过共振自己出现。不是搜索——是发现。',
    placeholder: '例如：需要一个擅长 React Native 的移动端开发...',
    chips: ['前端开发', '后端工程师', 'UI设计师', '产品经理'],
    centerContext: '技术互补性优先',
    cardTemplate: 'hackathon',
    planTemplate: 'team',
  },
  'skill-exchange': {
    id: 'skill-exchange',
    name: '技能交换',
    primary: '#FFE4B5',
    accent: '#D4A84A',
    bg: '#FFFDF5',
    hero: '你能教什么？想学什么？',
    heroDesc: '用你擅长的技能交换你想学的，在网络中找到对的人。',
    placeholder: '例如：我会弹吉他，想学摄影...',
    chips: ['编程', '设计', '音乐', '语言'],
    centerContext: '双向匹配度优先',
    cardTemplate: 'default',
    planTemplate: 'default',
  },
  recruit: {
    id: 'recruit',
    name: '智能招聘',
    primary: '#8FD5A3',
    accent: '#5AB87A',
    bg: '#F0FFF4',
    hero: '你在找什么样的人？',
    heroDesc: '描述岗位需求，让合适的候选人通过共振自己出现。',
    placeholder: '例如：需要 3 年以上经验的全栈工程师...',
    chips: ['工程师', '设计师', '产品经理', '运营'],
    centerContext: '经验与岗位匹配优先',
    cardTemplate: 'default',
    planTemplate: 'default',
  },
  matchmaking: {
    id: 'matchmaking',
    name: 'AI 相亲',
    primary: '#D4B8D9',
    accent: '#B093B8',
    bg: '#FDF5FF',
    hero: '描述你理想中的...',
    heroDesc: '不是筛选条件，而是共振——让价值观契合的人自己出现。',
    placeholder: '例如：希望找到一个喜欢户外运动、热爱阅读的人...',
    chips: ['运动', '艺术', '旅行', '美食'],
    centerContext: '价值观契合度优先',
    cardTemplate: 'default',
    planTemplate: 'default',
  },
};

export const DEFAULT_SCENE: SceneConfig = SCENES.hackathon;

export function getSceneConfig(sceneId: string): SceneConfig {
  return SCENES[sceneId] || DEFAULT_SCENE;
}

export function getAllSceneIds(): string[] {
  return Object.keys(SCENES);
}
