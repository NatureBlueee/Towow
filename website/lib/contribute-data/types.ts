export interface Task {
  name: string;
  oneLiner: string;
  target: string;
  tier: 1 | 2 | 'template';
  prdUrl: string;
}

export interface Track {
  id: string;
  name: string;
  color: string;
  goal: string;
  dependency?: string;
  tasks: Task[];
}
