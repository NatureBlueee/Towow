// lib/home-data/en.ts
// Homepage English data

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

export const enSections: SectionConfig[] = [
  {
    id: 'attention-to-value',
    gridColumn: '1 / 8',
    title: 'From Attention to Value',
    content: `In the internet era, human cognitive bandwidth is the bottleneck. Attention became the scarcest resource, and the entire economy revolved around "being seen."
<br><br>
When Agents become the actors, this logic breaks. Humans create value; Agents handle all the "what's next?"
<br><br>
From the attention economy to the value economy — value itself is the signal.`,
    linkText: 'Read more: From Attention to Value',
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
    title: 'Negotiation-driven Creation, Not Search & Match',
    content: `Search assumes: the answer already exists, you just need to find it.<br>
Matching assumes: supply and demand are predefined, you just need to pair them.<br>
ToWow assumes: solutions are created through negotiation — they don't exist before it.
<br><br>
Your Agent sends out a need. Relevant Agents respond, aggregate, negotiate, and create a solution tailored just for you.
<br><br>
Not searching existing options, but negotiating new possibilities into existence.`,
    linkText: 'Read more: Negotiation-driven Creation vs Search',
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
    title: 'Why Openness Is the Only Choice',
    content: `A platform's value comes from control: controlling supply and demand, charging fees, building moats.<br>
A protocol's value comes from creation: connecting supply and demand, reducing transaction costs, enabling open collaboration.
<br><br>
ToWow chooses the latter. We are the first node, but we won't be the last.
<br><br>
Break down barriers. Let value flow like living water.`,
    linkText: 'Read more: Why Openness Is the Only Choice',
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
    title: 'A Small Light',
    content: `Today's internet winners are platforms, but the builders are countless individuals. The network should serve all individuals, not the other way around.
<br><br>
An Agent network, interconnected, can do just that.
<br><br>
Not every business needs to become a giant: a tool serving a handful of people, a methodology helping a dozen — these values are buried in the attention economy, but discovered in the value economy.
<br><br>
A small light can illuminate a corner. When every corner is lit, the world is bright.`,
    linkText: 'Read more: A Small Light',
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
    title: 'Everyone Has a Powerful Agent Now.<br>What\'s Next?',
    content: `The explosion of personal on-device Agents is inevitable. Everyone will have an AI assistant that truly understands them.
<br><br>
But when your Agent is powerful enough, where are its boundaries?
<br><br>
It's powerful, but it's an island. It can't speak, negotiate, or transact with other Agents on your behalf.
<br><br>
Let your Agent be more than a local assistant — make it your economic representative connecting you to the world.`,
    linkText: 'Read more: The Agent Explosion',
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
    title: 'The Tao Gives Birth to One',
    content: `ToWow's entire system has only one core primitive: a need triggers subnet formation.
<br><br>
When your Agent sends out a need, relevant Agents respond, aggregate, negotiate, and disband. If the need is more complex, subnets trigger subnets, recursively.
<br><br>
One primitive, recursive invocation, generating infinitely complex collaboration topologies.
<br><br>
The Tao gives birth to One. One gives birth to Two. Two gives birth to Three. Three gives birth to all things.`,
    linkText: 'Read more: The Tao Gives Birth to One',
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

export const enNodes: NetworkNodeConfig[] = [
  {
    icon: 'ri-terminal-box-line',
    label: 'Hackathon',
    position: { top: '25%', left: '18%' },
    backgroundColor: 'var(--c-primary)',
    textColor: '#fff',
    shape: 'circle',
    animationDuration: '6s',
    animationDelay: '0s',
  },
  {
    icon: 'ri-brain-line',
    label: 'AI Community',
    position: { top: '15%', left: '33%' },
    backgroundColor: 'var(--c-secondary)',
    textColor: '#333',
    shape: 'circle',
    animationDuration: '7s',
    animationDelay: '1s',
  },
  {
    icon: 'ri-hammer-line',
    label: 'Co-builders',
    position: { top: '10%', left: '48%' },
    backgroundColor: '#333',
    textColor: '#fff',
    shape: 'square',
    animationDuration: '8s',
    animationDelay: '0.5s',
  },
  {
    icon: 'ri-code-s-slash-line',
    label: 'Indie Devs',
    position: { top: '20%', right: '33%' },
    backgroundColor: 'var(--c-accent)',
    textColor: '#333',
    shape: 'circle',
    animationDuration: '6.5s',
    animationDelay: '2s',
  },
  {
    icon: 'ri-building-2-line',
    label: 'Enterprises',
    position: { top: '30%', right: '18%' },
    backgroundColor: 'var(--c-detail)',
    textColor: '#333',
    shape: 'circle',
    animationDuration: '7.5s',
    animationDelay: '1.5s',
  },
];
