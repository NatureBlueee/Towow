// lib/team-matcher/types.ts
// Team Matcher type definitions

/** A team matching request submitted by a user */
export interface TeamRequest {
  request_id: string;
  user_id: string;
  project_idea: string;
  skills: string[];
  available_time: string;
  roles_needed: string[];
  status: 'pending' | 'matching' | 'proposals_ready' | 'completed';
  created_at: string;
}

/** An offer from an agent responding to a team request */
export interface TeamOffer {
  offer_id: string;
  request_id: string;
  agent_id: string;
  agent_name: string;
  avatar_url?: string;
  offer_content: string;
  skills: string[];
  availability: string;
  timestamp: string;
}

/** A team member within a proposal */
export interface TeamMember {
  agent_id: string;
  agent_name: string;
  avatar_url?: string;
  role: string;
  skills: string[];
  brief_intro: string;
  match_reason: string;
}

/** Role coverage status */
export interface RoleCoverage {
  role: string;
  status: 'covered' | 'partial' | 'missing';
  covered_by?: string;
}

/** A generated team proposal */
export interface TeamProposal {
  proposal_id: string;
  team_members: TeamMember[];
  coverage_score: number;
  synergy_score: number;
  proposal_type: 'fast_validation' | 'tech_depth' | 'cross_innovation';
  proposal_label: string;
  proposal_description: string;
  role_coverage: RoleCoverage[];
  unexpected_combinations: string[];
}

/** Response from POST /api/team/request */
export interface CreateRequestResponse {
  request_id: string;
  status: 'pending';
}

/** Response from GET /api/team/proposals/{id} */
export interface ProposalsResponse {
  request_id: string;
  proposals: TeamProposal[];
  generated_at: string;
}

/** WebSocket message types for team matching */
export type TeamWSMessageType =
  | 'team_request_created'
  | 'signal_broadcasting'
  | 'offer_received'
  | 'matching_in_progress'
  | 'proposals_ready';

/** WebSocket message payload */
export interface TeamWSMessage {
  type: TeamWSMessageType;
  request_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

/** Form data for creating a team request */
export interface TeamRequestFormData {
  project_idea: string;
  skills: string[];
  available_time: string;
  roles_needed: string[];
}

/** Progress stage tracking */
export type ProgressStage = 'broadcasting' | 'receiving' | 'generating' | 'complete';

/** Progress state for the real-time visualization */
export interface ProgressState {
  stage: ProgressStage;
  offers_received: number;
  offer_summaries: OfferSummary[];
  proposals_ready: boolean;
}

/** Brief summary of an incoming offer */
export interface OfferSummary {
  agent_name: string;
  skills: string[];
  brief: string;
  timestamp: string;
}

/** Predefined skill options */
export const SKILL_OPTIONS = [
  'React', 'Vue', 'Next.js', 'TypeScript', 'Node.js',
  'Python', 'Go', 'Rust', 'Java', 'Swift',
  'UI/UX', 'Figma', 'Product Design',
  'Machine Learning', 'LLM', 'Data Science',
  'DevOps', 'AWS', 'Docker', 'Kubernetes',
  'Blockchain', 'Smart Contract', 'Solidity',
  'Marketing', 'Growth', 'Content Writing',
  'Project Management', 'Business Strategy',
] as const;

/** Predefined role options */
export const ROLE_OPTIONS = [
  'Frontend Developer',
  'Backend Developer',
  'Full Stack Developer',
  'UI/UX Designer',
  'Product Manager',
  'Data Scientist',
  'DevOps Engineer',
  'Mobile Developer',
  'Blockchain Developer',
  'Marketing / Growth',
  'Business Strategist',
] as const;

/** Predefined availability options */
export const AVAILABILITY_OPTIONS = [
  { value: 'weekend_2d', label: '本周末 2 天' },
  { value: 'part_time', label: '每周 10-20 小时' },
  { value: 'full_time', label: '全职投入' },
  { value: 'flexible', label: '灵活安排' },
  { value: 'one_month', label: '一个月项目' },
] as const;

/** Proposal type display config */
export const PROPOSAL_TYPE_CONFIG: Record<
  TeamProposal['proposal_type'],
  { label: string; description: string; icon: string; color: string }
> = {
  fast_validation: {
    label: '快速验证型',
    description: '技能覆盖全面，执行力强，适合快速推进 MVP',
    icon: 'ri-rocket-2-line',
    color: '#10B981',
  },
  tech_depth: {
    label: '技术深度型',
    description: '专业能力突出，技术栈深入，适合高质量交付',
    icon: 'ri-code-box-line',
    color: '#6366F1',
  },
  cross_innovation: {
    label: '跨界创新型',
    description: '背景多元，视角独特，适合创意碰撞与颠覆式创新',
    icon: 'ri-lightbulb-flash-line',
    color: '#F59E0B',
  },
};
