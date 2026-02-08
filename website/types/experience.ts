export interface User {
  agent_id: string;
  display_name: string;
  avatar_url?: string;
  bio?: string;
  self_introduction?: string;
  profile_completeness?: number;
  skills: string[];
  specialties: string[];
  secondme_id: string;
}

export interface RequirementInput {
  title: string;
  description: string;
}

export interface Requirement {
  requirement_id: string;
  channel_id: string;
  requirement_text: string;
  priority: string;
  status: string;
  created_at: string;
}

export interface NegotiationMessage {
  message_id: string;
  channel_id: string;
  sender_id: string;
  sender_name: string;
  message_type: 'text' | 'system' | 'action';
  content: string;
  timestamp: string;
}

export type ExperienceState = 'INIT' | 'LOGIN' | 'REGISTERING' | 'READY' | 'SUBMITTING' | 'NEGOTIATING' | 'COMPLETED' | 'ERROR';
