import type { Stat, Transformation, Phase, Session, JourneyData } from './types';

const STATS: Stat[] = [
  { num: '19', label: 'Dev Days' },
  { num: '52', label: 'Git Commits' },
  { num: '41', label: 'Context Compacts' },
  { num: '18', label: 'PRD Documents' },
  { num: '3', label: 'Chat Sessions' },
];

const TRANSFORMATIONS: Transformation[] = [
  {
    label: 'From Code to Essence',
    time: '2/4 Turning Point',
    oneLiner: 'Stopping to think matters more than writing code',
    meaning: 'Abandon the engineer\'s inertia. Admit that "building it" is not the same as "understanding it"',
  },
  {
    label: 'From Complexity to Simplicity',
    time: '2/6 Epiphany',
    oneLiner: '"Projection as Function" -- one concept unifies the entire system',
    meaning: 'Good architecture is not designed complexity, but complexity emerging from simple recursive rules',
  },
  {
    label: 'From Closed to Open',
    time: '2/8 Co-creation',
    oneLiner: 'From building alone to inviting the community to co-create',
    meaning: 'The protocol itself should embody the protocol\'s value -- open collaboration',
  },
];

const PHASES: Phase[] = [
  {
    num: 1,
    name: 'Exploration & Understanding',
    dates: '1/21 - 1/22',
    narrative:
      'Everything started with understanding the OpenAgents framework. This isn\'t a "new project launch" story, but a "finding the path while standing on giants\' shoulders" journey. We discovered that ToWow\'s production environment had deviated from OpenAgents\' design paradigm -- custom routing and Mock channels that only logged but never communicated. Meanwhile, the Raphael demo project, though simple, fully demonstrated multi-Agent collaboration. After fixing Python import issues, we saw Agents autonomously coordinating for the first time. That moment confirmed the direction: don\'t reinvent the wheel, extend from proven patterns.',
    decisions: [
      'Build on Raphael demo code instead of fixing the deviated production code',
      'Use absolute imports + PYTHONPATH for module loading (not elegant, but effective)',
      'Established the "every user is a Worker Agent" direction',
    ],
    corrections: [],
    surprise:
      'ToWow production\'s _MockChannelHandle only logged without communicating -- not a bug, but a signal of wrong architectural choices. The cost of deviating from a mature framework is larger than expected.',
    quote: 'This is amazing!!!',
    quoteAuthor: 'Founder\'s reaction seeing multi-Agent collaboration running',
    tags: [
      { label: 'OpenAgents', color: 'code' },
      { label: 'Python', color: 'code' },
    ],
    stats: '11 commits / 2 compacts',
  },
  {
    num: 2,
    name: 'Backend Service Layer',
    dates: '1/27 - 1/29',
    narrative:
      'With a working skeleton, the next step was making it usable. SecondMe OAuth2 integration enabled real identity login; SQLite data layer persisted registration info; WebSocket enabled real-time state updates. The most important thing in this phase wasn\'t the technical implementation, but the founder\'s design philosophy -- "Keep it simple." When our technical plan was over-engineered (complex concurrency control, fine-grained rate limiting), the founder interrupted directly: "Too complex", "You\'re overthinking it." The server is powerful enough, users are few enough -- just make it work first.',
    decisions: [
      'SQLite instead of PostgreSQL (lightweight enough to validate)',
      'OAuth2 data flows one-way: SecondMe -> ToWow (don\'t push ToWow data back to SecondMe)',
      'Technical plan downgraded from "production-grade" to "validation-grade"',
    ],
    corrections: [
      '"Too complex" -- rejected the plan with rate limiting and concurrency control',
      '"You\'re overthinking it" -- don\'t assume users\' needs and constraints for them',
      '"Keep it simple" -- minimum viable is more important than perfect',
    ],
    surprise:
      'SecondMe API didn\'t return the openId field -- contrary to documentation. Used email as alternative identifier. Real systems always have surprises the docs don\'t mention.',
    quote: 'Don\'t question so much',
    quoteAuthor: 'Founder\'s response to an overly cautious Agent',
    tags: [
      { label: 'FastAPI', color: 'code' },
      { label: 'OAuth2', color: 'code' },
      { label: 'SQLite', color: 'code' },
    ],
    stats: '5 commits / 4 compacts',
  },
  {
    num: 3,
    name: 'Full-Stack Website',
    dates: '1/30',
    narrative:
      'The most intense day of the entire journey -- 20 commits, 8 context compacts, from a blank Next.js project to a deployable complete website. Homepage text was cut from "200 words per screen" to "under 100"; colors shifted from cold gray to warm cream; layout changed from grid cards to flowing gradients. The most meaningful part was the demo scenario design: the founder rejected the "indie musician organizing a concert" scenario because it didn\'t embody ToWow\'s core value. Changed to "finding a technical co-founder" -- the user thinks they need a person, but after negotiation discovers they actually need a capability. This demo scenario is itself a microcosm of ToWow\'s philosophy.',
    decisions: [
      'Next.js 16 + App Router + CSS Modules (no Tailwind, keep full control over styles)',
      'Removed grid/card design, switched to scrolling gradient background ("grids feel like caged order")',
      'Demo V2\'s 10-stage interactive animation: from demand shrinking to a dot to final proposal formation',
    ],
    corrections: [
      '"The website feels too cold/clinical" -- from #EEEEEE cold gray to #F8F6F3 warm cream. Not just color, but character',
      '"This indie musician concert thing is completely useless" -- demos must embody the philosophy, not just any scenario',
      '"The view is offset right... about 20% of the left side is invisible" -- attention to detail matters',
    ],
    surprise:
      'React Strict Mode caused WebSocket double mount/unmount -- the component mounts twice, and the first WebSocket gets cleaned up by the second unmount. Not an issue in production, but made developers think WebSocket was broken.',
    quote: 'You think you need something, then discover you don\'t.',
    quoteAuthor: 'Founder defining "Cognitive Shift"',
    tags: [
      { label: 'Next.js', color: 'design' },
      { label: 'UI/UX', color: 'design' },
      { label: 'WebSocket', color: 'code' },
    ],
    stats: '20 commits / 8 compacts',
  },
  {
    num: 4,
    name: 'Deployment & Operations',
    dates: '1/31',
    narrative:
      'From running locally to being accessible online -- Railway backend + Vercel frontend + Cloudflare CDN. This phase looks like "just deployment" but was actually full of details: OAuth callbacks needed to support multiple URLs (local and production), Cookie SameSite policies affected cross-domain auth, Vercel\'s Root Directory had to point to the monorepo subdirectory. Every "small problem" required understanding the entire request chain. Deployment isn\'t the end, but the starting point where everyone can see.',
    decisions: [
      'USE_REAL_AGENTS env variable to toggle real/simulated mode',
      'Cookie security policy controlled via environment variables (COOKIE_SECURE)',
      'Kept Experience V2 demo version while creating V3 real Agent version',
    ],
    corrections: [],
    surprise:
      'Vercel couldn\'t find the Next.js directory in the monorepo -- needed to set Root Directory to raphael/requirement_demo/towow-website in the Dashboard. Deployment config is easier to overlook than code.',
    quote: '',
    tags: [
      { label: 'Railway', color: 'deploy' },
      { label: 'Vercel', color: 'deploy' },
      { label: 'CDN', color: 'deploy' },
    ],
    stats: '8 commits / 3 compacts',
  },
  {
    num: 5,
    name: 'Deep Architecture Rethink',
    dates: '2/4 - 2/6',
    narrative:
      'The watershed of the entire journey. The founder said: "The design is ideal, but the architecture keeps making small mistakes." Then he made a surprising decision -- not asking me to fix bugs, but to stop and read documentation. Three core documents: whitepaper, technical brief, design log. After reading, not writing code, but discussing. Over the next 3 days, 14 context compacts, all spent on architectural thinking. From HDC hypervector encoding for signature broadcast, to multi-source adapters for Agent onboarding, to the "propose-aggregate" paradigm for the Skill system, to WOWOK blockchain protocol integration -- every round of discussion was a pursuit of "what is the essence?" In the final round, discussing the Service Agent crystallization mechanism, the founder said "essence and implementation aren\'t separated, it shouldn\'t be this complex." Then, after multiple leaps of thought, "Projection as Function" was born -- Agent is not an object, but a function result; projection is the only fundamental operation.',
    decisions: [
      'Three-tier resonance filtering: Bloom Filter (O(1)) -> HDC Resonance (O(D)) -> LLM (O(model))',
      '"Code guarantees > Prompt guarantees": use code for any deterministic logic, never rely on prompts',
      'Multi-round debate is net negative (-3.5%, DeepMind 2025), but parallel propose->aggregate is positive (+57-81%)',
      'WOWOK blockchain as "echo" mechanism -- waves go out, they must come back',
      '"Projection as Function": eliminated Profile update algorithms, drift prevention, state maintenance, and cold start problems',
    ],
    corrections: [
      '"Don\'t do MVP for MVP\'s sake, don\'t cut features just to cut features" -- minimum complete unit != feature cutting',
      '"You just executed for me, but you didn\'t think it through" -- don\'t build then think, think then build',
      '"Discuss to confirm understanding first, then write docs" -- alignment > efficiency',
      '"Essence and implementation aren\'t separated" -- gave birth to "Projection as Function"',
      '"Some problems shouldn\'t exist in the first place" -- the best solution is eliminating the problem itself',
    ],
    surprise:
      'Research found LLM "first-proposal bias" is as high as 10-30x (Microsoft 2025) -- this cannot be solved with prompts, must use code (wait barriers) to guarantee.',
    quote: 'The design is ideal, but the architecture keeps making small mistakes.',
    quoteAuthor: 'The sentence that triggered the transformation',
    tags: [
      { label: 'Architecture', color: 'doc' },
      { label: 'Design Log', color: 'doc' },
      { label: 'Arch Skill', color: 'doc' },
    ],
    stats: '1 commit / 14 compacts',
  },
  {
    num: 6,
    name: 'Hackathon Toolchain',
    dates: '2/7',
    narrative:
      'After the architecture was clear, back to engineering -- but different this time. Every tool was first thought through using the arch skill methodology: "what to build" and "why to build it," before implementation began. Team Matcher isn\'t "team matching," but a "collaboration possibility discovery engine"; Guide isn\'t a "tutorial," but a "cognitive lens." The most dramatic moment: the app stuck on "Broadcasting..." with no response -- tests passed but nothing actually worked, mock data masked real integration failures. The founder erupted: "Mock mode doesn\'t matter, just make it into a real application!" This echoed the architecture discussions\' principle of "don\'t simulate."',
    decisions: [
      'Used Opus 4.6 parallel Agent development (up to 9 working simultaneously)',
      'SecondMe Chat API integration: AI suggests form values based on Profile after login',
      'Abandoned mock-first strategy, directly faced the complexity of real integration',
    ],
    corrections: [
      '"Mock mode doesn\'t matter, make it into an application" -- don\'t demo for demo\'s sake',
      '"Don\'t talk about simulating five Agents responding" -- same principle',
      'Explicitly required Opus 4.6 over Sonnet 4.5 -- quality > speed',
    ],
    surprise:
      'The core problem with parallel Agent development wasn\'t code quality, but interface alignment. 4 Agents developing independently produced 5 integration bugs (WebSocket messages dropped, Channel ID mismatch, field name inconsistency, etc.). Needed a "cross-boundary reviewer" role.',
    quote:
      'Mock mode doesn\'t matter. I need all the login and everything. Just make it usable, not mock for mock\'s sake',
    quoteAuthor: 'Founder',
    tags: [
      { label: 'Team Matcher', color: 'code' },
      { label: 'SecondMe API', color: 'code' },
      { label: 'Full Stack', color: 'design' },
    ],
    stats: '1 commit / 8 compacts',
  },
  {
    num: 7,
    name: 'Co-creation Task System',
    dates: '2/8',
    narrative:
      'The last day of 19 days -- opening everything up to the community. 33 initial tasks refined to 18 through architectural evaluation -- "don\'t have tasks just to have tasks." 9 Opus 4.6 Agents wrote all 18 PRDs in parallel, each using arch + task-arch skill for philosophical alignment. The /contribute page went through three iterations: v1 too flashy, v2 too minimal, the founder said "don\'t be minimal just for minimalism\'s sake" -- every layer of information has a reason to exist, removing any layer loses meaning. This design principle is exactly the embodiment of ToWow\'s Section 0.9 (completeness != totality). One commit, 165 files, +18,795 lines.',
    decisions: [
      '33->18 task refinement: filtered using architectural principles ("What is the essence of this task? Is the problem it solves real?")',
      'Feishu-primary + website-secondary co-creation strategy (Bitable management + build in public)',
      'PRD writing used arch skill methodology, ensuring "worldview behind technical details"',
    ],
    corrections: [
      '"Don\'t have tasks just to have tasks" -- 33->18 not because too many, but because insufficient value',
      '"Don\'t be minimal just for minimalism\'s sake" -- extremely simple yet preserving complete meaning (core lesson from three page iterations)',
      'Corrected AI\'s misunderstanding of architectural design commitments -- "You misunderstood what design commitments mean"',
    ],
    surprise:
      'When 9 Agents wrote PRDs in parallel, each had a slightly different understanding of "ToWow philosophy" -- this is itself an instance of "projection": the same architecture document, through different Agent "lenses," produces different but individually valuable PRDs.',
    quote: 'Don\'t be minimal just for minimalism\'s sake.',
    quoteAuthor: 'A design principle perfectly corresponding to Section 0.9',
    tags: [
      { label: '18 PRDs', color: 'doc' },
      { label: '/contribute', color: 'design' },
      { label: 'Feishu', color: 'doc' },
      { label: 'Deploy', color: 'deploy' },
    ],
    stats: '1 commit (165 files, +18,795 lines) / 4 compacts',
  },
];

const SESSIONS: Session[] = [
  {
    label: 'Session 1',
    dateRange: 'Main Dev Session / 1/26 - 2/5',
    color: '#8B6A90',
    compacts: [
      { num: 1, date: '1/26', title: 'Understand project + Fix OpenAgents imports + First multi-Agent collaboration', detail: 'First deep dive into ToWow code. Compared and found Raphael demo uses native OpenAgents patterns (event-driven, BaseMod), while production deviated (custom routing, Mock channel only logging). Python relative import issues prevented Mod loading, bypassed with sys.path. After fixing, successfully ran the complete flow: demand submission, channel creation, Agent invitation, task distribution, coordination summary.' },
      { num: 2, date: '1/27', title: 'SecondMe OAuth2 login + Dynamic Agent creation', detail: 'Created web registration service with SecondMe OAuth2 authorization code flow. Users automatically get a Worker Agent created and registered to the network after login. Security review found 8 issues, all fixed. 17 unit tests passed.' },
      { num: 3, date: '1/27', title: 'GitHub upload + OAuth testing + URL encoding fix', detail: 'Configured .gitignore to exclude large files, pushed to GitHub. SecondMe OAuth testing revealed callback URL being double-encoded, removed manual encoding. Discovered SecondMe API doesn\'t return the documented openId field, used email as identifier instead.' },
      { num: 4, date: '1/29', title: 'Backend production packaging -- SQLite + WebSocket', detail: 'Founder required 2,000-3,000+ concurrent support while emphasizing "Keep it simple." First technical plan was over-engineered and rejected. Simplified to SQLite + SQLAlchemy data persistence and WebSocket real-time push. 16 API tests passed.' },
      { num: 5, date: '1/29', title: 'Tests + API docs + Frontend HTML -> Next.js migration', detail: 'Complete API tests passed, generated API documentation. Started migrating HTML homepage and article detail pages to Next.js 14 (App Router), using CSS Modules + CSS Variables.' },
      { num: 6, date: '1/30', title: 'Experience page + SecondMe data integration research', detail: 'Parallel development of experience page: SecondMe OAuth2 login, demand submission, real-time negotiation display. Researched SecondMe API data structure to reduce manual user input. Founder demanded "start everything in parallel and keep developing."' },
      { num: 7, date: '1/30', title: 'Homepage content + Article system + Screen ratio fix', detail: 'Fixed screen ratio (body font 19px -> 16px) and responsive layout. Homepage Hero title set to "The Internet Redesigned for Agents." Created article list page with 3 complete articles. Founder noted "the protocol\'s value should come from creation, not adoption."' },
      { num: 8, date: '1/30', title: 'Article content + Warm color scheme + Scroll gradient background', detail: 'Added "Dao Sheng Yi" and "A Tiny Light" articles. Founder felt the website was too cold/clinical -- "the grid behind gives more of a caged, ordered feeling." Removed grid lines, added scroll gradient background. From #EEEEEE cold gray to #F8F6F3 warm cream.' },
      { num: 9, date: '1/30', title: 'OAuth fix + Real-time negotiation + Typewriter effect + Vercel deploy', detail: 'Fixed OAuth callback not redirecting (returning JSON instead of redirect), implemented demand submission and real-time negotiation display. Added typewriter effect for streaming messages to improve UX. Code review found hardcoded password hash, moved to env variables. Deployed to Vercel + CDN.' },
      { num: 10, date: '1/30', title: 'Redis Session + beads task management + UI updates', detail: 'Created Redis Session storage migration docs and 4 implementation files. UI tweaks: changed "Join Network" to "Try Demo," updated contact email, added WeChat group QR code, removed not-yet-ready GitHub and Twitter links.' },
      { num: 11, date: '1/30', title: '"One-click experience" + "Find a tech co-founder" demo scenario', detail: 'Implemented one-click experience feature. Founder rejected "indie musician concert" scenario. Changed to "finding a tech co-founder" -- demonstrating "Cognitive Shift": user thinks they need a "tech co-founder," discovers they actually need "the ability to validate ideas quickly." Designed 7 Agents and 6 negotiation stages.' },
      { num: 12, date: '1/30', title: 'WebSocket CORS fix + Experience UI optimization + Vercel binding', detail: 'WebSocket couldn\'t send cookies cross-domain due to samesite="lax." Added /ws/demo/ unauthenticated endpoint + frontend auto-detection of cross-domain. Moved user info to fixed top-right position, added collapsible Profile card. Bound Vercel to GitHub for auto-deploy.' },
      { num: 13, date: '1/30', title: 'SecondMe data expansion + Mobile adaptation + Scroll gradient fix', detail: 'Founder said "the basic info from SecondMe is too little" -- added selfIntroduction, profileCompleteness and other new fields. Fixed background gradient to fixed positioning. Full site mobile responsive adaptation (17 files, 1,134 lines).' },
      { num: 14, date: '1/30', title: 'Demo V2 -- 10-stage interactive animation', detail: 'Founder described the complete interaction flow in detail: demand shrinks to a dot, shoots out lines, background circles flash for broadcast, Agent discovery and classification, green Agents converge, response display, information convergence center, filtering and point-to-point negotiation, final proposal. Implemented a 10-stage state machine animation.' },
      { num: 15, date: '1/31', title: 'Railway deploy + Multi-env OAuth + Experience V3 (real Agents)', detail: 'Railway backend + Vercel frontend deployment. Supported local and production OAuth callbacks. Created experience-v3 using real OpenAgents data, kept experience-v2 demo version.' },
      { num: 16, date: '1/31', title: 'WebSocket disconnect investigation + React StrictMode double mount', detail: 'WebSocket disconnected immediately after connecting -- found it was React Strict Mode\'s double mount/unmount. Dev-only issue, production unaffected. Investigated why OpenAgents network stopped working.' },
      { num: 17, date: '2/4', title: 'Recruitment article + Hero adjustment + Beginning of architecture reflection', detail: 'Added co-creation recruitment article, modified Hero section. Turning point: founder expressed fundamental concerns about the architecture -- "The design is ideal, but the architecture keeps making small mistakes." Provided three core documents, requiring "read these three documents first, then we\'ll discuss the technical architecture." Shifted from "doing" to "thinking."' },
      { num: 18, date: '2/5', title: 'Read three documents + "Don\'t do MVP for MVP\'s sake"', detail: 'Read whitepaper, technical brief, design log. Founder emphasized "Don\'t do MVP for MVP\'s sake, don\'t cut features just to cut features" -- minimum complete unit doesn\'t mean cutting features. The atom must be complete and recursive in itself.' },
      { num: 19, date: '2/5', title: 'Continue reading docs + Prepare for deep architecture discussion', detail: 'Continued digesting three core documents, organized technical concepts and architecture decision records. Preparing for upcoming deep discussions. This is the necessary cost of "slowing down."' },
    ],
  },
  {
    label: 'Session 2',
    dateRange: 'Hackathon Toolchain / 2/7',
    color: '#C47030',
    compacts: [
      { num: 20, date: '2/7', title: 'Hackathon toolchain launch -- Guide + Team Matcher + towow-dev Skill', detail: 'Launched ToWow hackathon toolchain development. Used arch skill methodology to think about each deliverable\'s essence -- Guide is not a tutorial but a "cognitive lens," Team Matcher is not a matching tool but a "collaboration possibility discovery engine." Used Opus 4.6 parallel Agent development.' },
      { num: 21, date: '2/7', title: 'Team Matcher backend + frontend parallel dev', detail: 'Parallel development of Team Matcher backend API, teaming engine, and frontend UI. Founder explicitly required Opus 4.6 over Sonnet 4.5. Implemented route refactoring from /team to /apps/team-matcher, established frontend-backend parallel development task dependencies.' },
      { num: 22, date: '2/7', title: 'SecondMe Chat API integration design', detail: 'Entered Plan Mode to design SecondMe Chat API integration strategy. Founder provided complete API documentation. This is the upgrade from "user manual input" to "AI-assisted filling" -- AI suggests form content based on Profile after login.' },
      { num: 23, date: '2/7', title: 'SecondMe Chat API implementation + Teaming engine LLM integration', detail: 'Implemented SSE streaming call to SecondMe Chat API. Created team_prompts.py with LLM teaming suggestion system/user prompts, JSON extraction and standardization.' },
      { num: 24, date: '2/7', title: 'Wave 2 parallel dev + 5 integration bug fixes', detail: 'Opus 4.6 Agents parallel-modified teaming engine and WebSocket streaming. Code review found 5 critical integration bugs: WebSocket messages dropped, Channel ID mismatch, field name inconsistency, API URL path errors, access_token not persisted. All fixed.' },
      { num: 25, date: '2/7', title: '"Don\'t simulate, make it real" -- User eruption', detail: 'App stuck on "Broadcasting..." with no response. Tests passed but nothing actually worked -- mock data masked real integration failures. Founder deeply frustrated: "Mock mode doesn\'t matter, make it into a real application," "Don\'t talk about simulating five Agents responding."' },
      { num: 26, date: '2/7', title: 'UX improvements + Skill tag expansion + SecondMe auto-fill concept', detail: 'Progress page evolved from "Broadcasting..." to showing actual information. Skill tags expanded (added AI-native and non-technical tags). Conceptualized SecondMe auto-fill: AI suggests form values based on Profile after login.' },
      { num: 27, date: '2/7', title: 'SecondMe auto-fill implementation + Plan Mode', detail: 'Implemented SecondMe auto-fill: after login, calls Chat API to suggest form values based on Profile + hackathon context. Typewriter effect fills in character by character -- UX detail makes the automation process perceivable rather than sudden.' },
    ],
  },
  {
    label: 'Session 3',
    dateRange: 'Architecture + Co-creation System / 2/6 - 2/8',
    color: '#5A8A64',
    compacts: [
      { num: 28, date: '2/6', title: 'Signature broadcast design -- HDC + Three-tier resonance filtering', detail: 'Designed signal resonance mechanism: Bloom Filter (90% filtering, 100ns/check), HDC Resonance Detection (9% filtering, 1us), LLM deep understanding (1% processing, 10ms). Hyperdimensional Computing core: 10,000-dim binary hypervectors, SimHash encoding preserving semantics. Founder\'s key insight: "broadcast and filtering are the same logic executed twice."' },
      { num: 29, date: '2/6', title: 'Agent onboarding + Skill system design', detail: 'Discussed how Agents join the network. Founder proposed "Agent IS your Profile" -- users don\'t need to "build an Agent," just provide information. Skill system research reviewed 20+ papers, found multi-round debate is net negative (-3.5%), but parallel propose-to-aggregate is positive (+57-81%).' },
      { num: 30, date: '2/6', title: 'Architecture meta-review -- Self-consistency + Whitepaper alignment', detail: 'Comprehensive review of completed architecture chapters for internal consistency. Cross-validated against whitepaper. Checked whether "beauty," "minimalism," and "minimum complete unit" principles were met. This round was "meta-review" -- not writing new content, but checking if existing content is self-consistent.' },
      { num: 31, date: '2/6', title: 'Offer sedimentation -> Service Agent crystallization + Design principles', detail: 'Deep discussion on how Offers sediment into Service Agent crystallization model. Extracted new design principles -- "demand != requirement" (demand is abstract tension, requirement is concrete hypothetical solution). Ensured engineering serves business goals.' },
      { num: 32, date: '2/6', title: 'Meta-review -- "The one question that unlocks all questions" + Value signal', detail: 'Architecture meta-review: blind spots, self-consistency, business-engineering alignment. Founder asked "What is the one question that unlocks all questions?" The answer emerged: value signal / feedback loop -- how does the system know it\'s working? Waves went out, but never came back. This is "a pipe, not a field."' },
      { num: 33, date: '2/6', title: 'WOWOK blockchain integration -- "Waves come back"', detail: 'Founder corrected the approach: "You just executed for me, but you didn\'t think it through." Should discuss to confirm understanding first, then write docs. Deep understanding of WOWOK protocol (Machine/Progress = essence vs implementation, Service/Order = essence vs implementation, Guard = verification engine, not signature itself).' },
      { num: 34, date: '2/6', title: 'WOWOK core concepts + Resonance threshold k* mechanism', detail: 'Confirmed understanding of WOWOK\'s 9 core objects. Designed resonance threshold strategy: k* is not a preset constant, but computed from expected response count. One k* rule uniformly solved 5 problems: initial value, pass-rate expectation, scenario variation, adaptive adjustment, and cold start.' },
      { num: 35, date: '2/6', title: '"Projection as Function" -- The architectural epiphany', detail: 'While discussing the Service Agent crystallization mechanism, the plan became overly complex. Founder challenged: "Essence and implementation aren\'t separated. It shouldn\'t be this complex." After multiple leaps of thought, the core principle was established: Agent = result of a projection function, not a stateful object. Profile Data lives in the data source, ToWow only projects. One concept eliminated four problems.' },
      { num: 36, date: '2/7', title: 'A2A Hackathon strategy -- Toolchain design thinking', detail: 'Designed toolchain for the A2A Hackathon. Used arch skill methodology to think about each deliverable -- not "get it done" but "get it right." Guide = cognitive lens, Team Matcher = collaboration possibility discovery engine, towow-dev skill = engineering leader role.' },
      { num: 37, date: '2/7', title: 'Architecture document full update -- Design Log backfill', detail: 'Founder clarified "we haven\'t started implementation yet, we\'re purely doing architecture." Backfilled insights from Design Log #001/#002/#003 into ARCHITECTURE_DESIGN.md. Deliberately did not touch implementation code.' },
      { num: 38, date: '2/8', title: 'Task/PRD Skill creation + 33->18 task refinement', detail: 'Founder requested a dedicated PRD Skill. Used arch skill to re-evaluate 33 tasks. Founder corrected the evaluation direction multiple times -- "Don\'t have tasks just to have tasks." Refined to 18: not because too many, but because some tasks\' "essential problems" weren\'t real enough.' },
      { num: 39, date: '2/8', title: '9 Agents write 18 PRDs in parallel', detail: 'Founder corrected my misunderstanding of architectural design commitments. Then launched 9 Opus 4.6 Agents to write all 18 PRDs in parallel, each using arch + task-arch skill. This is an instance of "projection" -- the same architecture document, through 9 different Agent lenses, produces 18 distinctive PRDs.' },
      { num: 40, date: '2/8', title: 'Delivery planning -- Feishu + website /contribute page', detail: '9 Agents completed 18 PRDs. Founder\'s decision: Feishu-primary (Bitable + manual paste management), website-secondary (build in public). Created /contribute page v1 and Feishu CSV import file.' },
      { num: 41, date: '2/8', title: '/contribute three iterations + Feishu announcement + Deploy', detail: '/contribute page three iterations: too flashy -> too minimal -> "don\'t be minimal just for minimalism\'s sake." Added field labels, target descriptions, "Task 1/2/3" numbering. Created Feishu group announcement document. One commit, 165 files, +18,795 lines. Deployed online, open co-creation infrastructure complete.' },
    ],
  },
];

export const enData: JourneyData = {
  stats: STATS,
  transformations: TRANSFORMATIONS,
  phases: PHASES,
  sessions: SESSIONS,
};
