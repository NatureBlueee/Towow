// lib/team-matcher/api.ts
// Team Matcher API client with mock data fallback

import {
  TeamRequest,
  TeamRequestFormData,
  CreateRequestResponse,
  ProposalsResponse,
  TeamOffer,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

/**
 * Submit a new team matching request.
 * Falls back to mock when backend is unavailable.
 */
export async function createTeamRequest(
  data: TeamRequestFormData & { user_id: string }
): Promise<CreateRequestResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/team/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    // Mock fallback
    return {
      request_id: `mock-${Date.now()}`,
      status: 'pending',
    };
  }
}

/**
 * Submit an offer for a team request.
 */
export async function submitTeamOffer(offer: {
  request_id: string;
  agent_id: string;
  offer_content: string;
  skills: string[];
  availability: string;
}): Promise<{ success: boolean }> {
  try {
    const res = await fetch(`${API_BASE}/api/team/offer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(offer),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return { success: true };
  }
}

/**
 * Get the status of a team request.
 */
export async function getTeamRequest(requestId: string): Promise<TeamRequest> {
  try {
    const res = await fetch(`${API_BASE}/api/team/request/${requestId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return getMockRequest(requestId);
  }
}

/**
 * Get generated proposals for a request.
 */
export async function getTeamProposals(
  requestId: string,
  maxProposals: number = 3
): Promise<ProposalsResponse> {
  try {
    const res = await fetch(
      `${API_BASE}/api/team/proposals/${requestId}?max_proposals=${maxProposals}`
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return getMockProposals(requestId);
  }
}

// ============================================
// Mock Data for Development
// ============================================

function getMockRequest(requestId: string): TeamRequest {
  return {
    request_id: requestId,
    user_id: 'demo-user',
    project_idea: 'AI 健康助手 - 用 LLM 分析饮食数据并给出个性化建议',
    skills: ['React', 'Python', 'LLM'],
    available_time: 'weekend_2d',
    roles_needed: ['Frontend Developer', 'Backend Developer', 'UI/UX Designer'],
    status: 'proposals_ready',
    created_at: new Date().toISOString(),
  };
}

export function getMockOffers(): TeamOffer[] {
  return [
    {
      offer_id: 'offer-1',
      request_id: 'mock-1',
      agent_id: 'agent-alex',
      agent_name: 'Alex Chen',
      offer_content: '全栈工程师，擅长 React + Python，对健康领域有个人兴趣',
      skills: ['React', 'Next.js', 'Python', 'FastAPI'],
      availability: '本周末 2 天',
      timestamp: new Date().toISOString(),
    },
    {
      offer_id: 'offer-2',
      request_id: 'mock-1',
      agent_id: 'agent-miya',
      agent_name: 'Miya Wang',
      offer_content: 'UI/UX 设计师，有医疗健康类 APP 的设计经验',
      skills: ['UI/UX', 'Figma', 'Product Design', 'User Research'],
      availability: '灵活安排',
      timestamp: new Date().toISOString(),
    },
    {
      offer_id: 'offer-3',
      request_id: 'mock-1',
      agent_id: 'agent-kevin',
      agent_name: 'Kevin Liu',
      offer_content: 'ML 工程师，专注 NLP/LLM 应用，有医疗文本处理经验',
      skills: ['Python', 'Machine Learning', 'LLM', 'Data Science'],
      availability: '每周 10-20 小时',
      timestamp: new Date().toISOString(),
    },
    {
      offer_id: 'offer-4',
      request_id: 'mock-1',
      agent_id: 'agent-sarah',
      agent_name: 'Sarah Li',
      offer_content: '营养师 + 业余前端开发者，可以提供专业的营养学视角',
      skills: ['Nutrition Science', 'React', 'Content Writing'],
      availability: '本周末 2 天',
      timestamp: new Date().toISOString(),
    },
    {
      offer_id: 'offer-5',
      request_id: 'mock-1',
      agent_id: 'agent-tom',
      agent_name: 'Tom Zhang',
      offer_content: '后端架构师，擅长高并发系统设计，对 AI 应用感兴趣',
      skills: ['Go', 'Node.js', 'DevOps', 'AWS'],
      availability: '全职投入',
      timestamp: new Date().toISOString(),
    },
  ];
}

function getMockProposals(requestId: string): ProposalsResponse {
  return {
    request_id: requestId,
    generated_at: new Date().toISOString(),
    proposals: [
      {
        proposal_id: 'prop-1',
        proposal_type: 'fast_validation',
        proposal_label: '快速验证型',
        proposal_description: '技能覆盖全面，成员可用时间匹配度高，适合快速推出 MVP',
        coverage_score: 0.92,
        synergy_score: 0.78,
        team_members: [
          {
            agent_id: 'agent-alex',
            agent_name: 'Alex Chen',
            role: 'Full Stack Lead',
            skills: ['React', 'Next.js', 'Python', 'FastAPI'],
            brief_intro: '全栈工程师，5 年经验',
            match_reason: '技术栈与项目需求高度匹配，可同时承担前后端开发',
          },
          {
            agent_id: 'agent-miya',
            agent_name: 'Miya Wang',
            role: 'UI/UX Designer',
            skills: ['UI/UX', 'Figma', 'Product Design'],
            brief_intro: 'UI/UX 设计师，有医疗 APP 经验',
            match_reason: '健康类产品设计经验丰富，能快速产出高质量界面',
          },
          {
            agent_id: 'agent-kevin',
            agent_name: 'Kevin Liu',
            role: 'ML Engineer',
            skills: ['Python', 'Machine Learning', 'LLM'],
            brief_intro: 'ML 工程师，NLP 专家',
            match_reason: 'LLM 应用经验直接匹配项目核心需求',
          },
        ],
        role_coverage: [
          { role: 'Frontend', status: 'covered', covered_by: 'Alex Chen' },
          { role: 'Backend', status: 'covered', covered_by: 'Alex Chen' },
          { role: 'UI/UX', status: 'covered', covered_by: 'Miya Wang' },
          { role: 'ML/AI', status: 'covered', covered_by: 'Kevin Liu' },
          { role: 'DevOps', status: 'partial' },
        ],
        unexpected_combinations: [],
      },
      {
        proposal_id: 'prop-2',
        proposal_type: 'tech_depth',
        proposal_label: '技术深度型',
        proposal_description: '后端架构能力强，AI 工程深入，适合打造技术壁垒',
        coverage_score: 0.85,
        synergy_score: 0.88,
        team_members: [
          {
            agent_id: 'agent-tom',
            agent_name: 'Tom Zhang',
            role: 'Backend Architect',
            skills: ['Go', 'Node.js', 'DevOps', 'AWS'],
            brief_intro: '后端架构师，10 年经验',
            match_reason: '能构建高可用的后端架构，确保系统可扩展性',
          },
          {
            agent_id: 'agent-kevin',
            agent_name: 'Kevin Liu',
            role: 'ML Lead',
            skills: ['Python', 'Machine Learning', 'LLM', 'Data Science'],
            brief_intro: 'ML 工程师，NLP 专家',
            match_reason: 'LLM + 数据科学双重能力，可打造深度 AI 功能',
          },
          {
            agent_id: 'agent-alex',
            agent_name: 'Alex Chen',
            role: 'Frontend Developer',
            skills: ['React', 'Next.js', 'TypeScript'],
            brief_intro: '全栈工程师，前端精通',
            match_reason: 'React 专家，可打造流畅的用户交互体验',
          },
        ],
        role_coverage: [
          { role: 'Frontend', status: 'covered', covered_by: 'Alex Chen' },
          { role: 'Backend', status: 'covered', covered_by: 'Tom Zhang' },
          { role: 'UI/UX', status: 'missing' },
          { role: 'ML/AI', status: 'covered', covered_by: 'Kevin Liu' },
          { role: 'DevOps', status: 'covered', covered_by: 'Tom Zhang' },
        ],
        unexpected_combinations: [],
      },
      {
        proposal_id: 'prop-3',
        proposal_type: 'cross_innovation',
        proposal_label: '跨界创新型',
        proposal_description: '营养师 + 工程师的独特组合，能从专业视角重新定义产品方向',
        coverage_score: 0.80,
        synergy_score: 0.95,
        team_members: [
          {
            agent_id: 'agent-sarah',
            agent_name: 'Sarah Li',
            role: 'Domain Expert & Frontend',
            skills: ['Nutrition Science', 'React', 'Content Writing'],
            brief_intro: '营养师 + 业余开发者',
            match_reason: '专业营养学背景能确保 AI 建议的科学性和可信度',
          },
          {
            agent_id: 'agent-alex',
            agent_name: 'Alex Chen',
            role: 'Tech Lead',
            skills: ['React', 'Next.js', 'Python', 'FastAPI'],
            brief_intro: '全栈工程师',
            match_reason: '技术全面，可快速实现跨领域创意',
          },
          {
            agent_id: 'agent-kevin',
            agent_name: 'Kevin Liu',
            role: 'AI Engineer',
            skills: ['Python', 'Machine Learning', 'LLM'],
            brief_intro: 'ML 工程师',
            match_reason: 'LLM 能力 + 营养师专业知识 = 更准确的健康建议引擎',
          },
          {
            agent_id: 'agent-miya',
            agent_name: 'Miya Wang',
            role: 'UX Designer',
            skills: ['UI/UX', 'Figma', 'User Research'],
            brief_intro: 'UI/UX 设计师',
            match_reason: '可将复杂的营养数据转化为直观易懂的界面',
          },
        ],
        role_coverage: [
          { role: 'Frontend', status: 'covered', covered_by: 'Alex Chen' },
          { role: 'Backend', status: 'covered', covered_by: 'Alex Chen' },
          { role: 'UI/UX', status: 'covered', covered_by: 'Miya Wang' },
          { role: 'ML/AI', status: 'covered', covered_by: 'Kevin Liu' },
          { role: 'Domain Expert', status: 'covered', covered_by: 'Sarah Li' },
        ],
        unexpected_combinations: [
          '营养师 Sarah + ML 工程师 Kevin 的组合：专业营养学知识能让 LLM 的健康建议更科学、更个性化，这是纯技术团队无法达到的深度',
          '营养师 Sarah + 设计师 Miya 的组合：专业视角 + 设计能力，能将复杂营养数据转化为用户真正能理解和行动的界面',
        ],
      },
    ],
  };
}
