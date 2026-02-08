import type { Track } from './types';

export const enTracks: Track[] = [
  {
    id: 'core',
    name: 'Core Validation',
    color: '#D4B8D9',
    goal: 'Validate ToWow\'s core technical hypotheses -- HDC encoding, resonance detection, negotiation engine -- and measure their real-world effectiveness.',
    dependency: 'Experiment Design -> Encoding Validation -> Visualization (sequential)',
    tasks: [
      {
        name: 'Minimum Validation Experiment Design', tier: 1,
        oneLiner: 'Design minimal experiments to quantify the effectiveness of ToWow\'s 5 core hypotheses. The starting point for all subsequent validation.',
        target: 'People with experiment design skills (research / data science background)',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/H4_minimum_validation_experiments.md',
      },
      {
        name: 'HDC Encoding Strategy Validation', tier: 1,
        oneLiner: 'Compare encoding methods to find the optimal "text -> hypervector" strategy. Determines the system\'s signal quality.',
        target: 'Developers or researchers with NLP / ML experience',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/A1_hdc_encoding.md',
      },
      {
        name: 'Hypervector Space Visualization', tier: 2,
        oneLiner: '"See" how Agents are distributed and resonate in HDC space. Verify whether encoding matches intuition.',
        target: 'Developers with frontend and data visualization experience',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/H5_hypervector_visualization.md',
      },
    ],
  },
  {
    id: 'positioning',
    name: 'Positioning & Outreach',
    color: '#D4F4DD',
    goal: 'Articulate what ToWow is and isn\'t. Help people from different backgrounds understand the value of the Response Paradigm.',
    dependency: 'Competitive Analysis -> Popular Science Article -> Technical Blog (progressive); Concept Translation, Glossary, Case Story can start independently',
    tasks: [
      {
        name: 'Competitive / Reference System Analysis', tier: 1,
        oneLiner: 'Systematically analyze ToWow\'s paradigm-level differences from AutoGen, recommendation systems, Fetch.ai, etc. Find clear differentiation.',
        target: 'People familiar with the AI Agent ecosystem',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/A5_competitive_analysis.md',
      },
      {
        name: 'Response Paradigm Popular Article', tier: 1,
        oneLiner: 'Zero technical barrier. 3 minutes to understand the fundamental difference between "search" and "response." For the widest audience.',
        target: 'Strong writers (no technical background needed)',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/D1_response_paradigm_article.md',
      },
      {
        name: 'Concept Translation (Cross-domain)', tier: 1,
        oneLiner: 'Help people in recruiting, blockchain, investment, and product domains understand ToWow in their own language.',
        target: 'People with cross-domain backgrounds',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/H1_concept_translation.md',
      },
      {
        name: 'Core Glossary (Bilingual)', tier: 2,
        oneLiner: '30-40 core terms in Chinese-English with technical meaning and philosophical connotations preserved.',
        target: 'People fluent in technical English who understand philosophical concepts',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/C1_glossary.md',
      },
      {
        name: '"Projection as Function" Technical Blog', tier: 2,
        oneLiner: 'Explain the core insight for technical readers: Agents are functions, not objects. Projection is the fundamental operation.',
        target: 'Developers with technical writing skills',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/D2_projection_as_function_blog.md',
      },
      {
        name: 'From Demand to Discovery: Case Story', tier: 2,
        oneLiner: 'A complete story that lets people feel the power of the Response Paradigm in discovering unexpected value.',
        target: 'People with storytelling ability',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/D5_demand_to_discovery_story.md',
      },
    ],
  },
  {
    id: 'product',
    name: 'Scenes & Products',
    color: '#FFE4B5',
    goal: 'Turn ideas into usable applications. Validate whether the ToWow protocol creates real value in actual scenes.',
    dependency: 'Scene Modeling -> Scene Template -> Indie App Template (progressive); Prompt Engineering is an independent path',
    tasks: [
      {
        name: 'Hackathon Teaming Scene Modeling', tier: 1,
        oneLiner: 'Systematically analyze the full user journey from finding teammates to forming a team. ToWow\'s first real-world scene.',
        target: 'Hackathon veterans / Product managers',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/B1_hackathon_teaming.md',
      },
      {
        name: 'Prompt Engineering Research', tier: 1,
        oneLiner: 'Systematically optimize LLM prompts for ToWow\'s 6 core Skills to improve negotiation quality.',
        target: 'Developers with Prompt engineering experience',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/H2_prompt_engineering.md',
      },
      {
        name: 'Scene Modeling Template', tier: 'template',
        oneLiner: 'Provide co-creators with a standard process and template for modeling new domain scenes.',
        target: 'Anyone from any domain (recruiting, hospitality, education...)',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/T1_scene_modeling_template.md',
      },
      {
        name: 'Indie App Template', tier: 'template',
        oneLiner: 'A task template for building real products with ToWow\'s philosophy. Helps developers get started quickly.',
        target: 'Developers',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/T2_indie_app_template.md',
      },
    ],
  },
  {
    id: 'frontier',
    name: 'Frontier Research',
    color: '#F9A87C',
    goal: 'Long-term technical reserves. These directions don\'t affect V1 development, but are crucial for the network\'s long-term evolution.',
    dependency: 'Four independent directions. Claim based on personal interest.',
    tasks: [
      {
        name: 'Distributed Resonance Network Survey', tier: 2,
        oneLiner: 'V1 uses centralized broadcast; long-term needs distributed. Produce an academic survey as knowledge reserve.',
        target: 'People with academic research skills',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/A2_distributed_resonance_survey.md',
      },
      {
        name: 'Economic Incentive Model Exploration', tier: 2,
        oneLiner: 'The network needs incentive mechanisms for participation. Map out available directions and trade-offs.',
        target: 'People with economics / game theory or token design knowledge',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/A3_economic_incentive_model.md',
      },
      {
        name: 'Security Model & Data Ownership Survey', tier: 2,
        oneLiner: 'ToWow involves personal data and Agent behavior. How to ensure security and privacy.',
        target: 'People with security / privacy research background',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/A4_security_data_ownership.md',
      },
      {
        name: 'Sui Chain Cost & Performance Benchmark', tier: 2,
        oneLiner: 'Real-world benchmarking of WOWOK on-chain operations on Sui. Provide data support for the on-chain execution layer.',
        target: 'People with Sui / Move development experience',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/A6_sui_chain_benchmark.md',
      },
    ],
  },
  {
    id: 'ecosystem',
    name: 'Developer Ecosystem',
    color: '#E8F3E8',
    goal: 'Enable other developers to understand ToWow and build with it. Lower the barrier to entry.',
    tasks: [
      {
        name: 'Developer Starter Kit', tier: 1,
        oneLiner: 'Help developers understand ToWow and start building their own scenes within 30 minutes.',
        target: 'Experienced developers who understand ToWow\'s philosophy',
        prdUrl: 'https://github.com/NatureBlueee/Towow/blob/main/docs/tasks/H3_developer_starter_kit.md',
      },
    ],
  },
];
