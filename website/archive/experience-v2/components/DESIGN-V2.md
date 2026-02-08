# ToWow Demo V2 - Complete Interaction Flow Design

## Design System

Based on UI/UX Pro Max recommendations:
- **Pattern**: Immersive/Interactive Experience
- **Style**: Soft UI Evolution (modern aesthetics, subtle depth)
- **Colors**: Existing palette (--c-primary: #D4B8D9, --c-bg: #F8F6F3)
- **Typography**: Inter / NotoSansHans
- **Key Effects**: Improved shadows, 200-300ms transitions, WCAG AA+

## State Machine Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DEMO V2 STATE MACHINE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [input] ──submit──> [launch] ──auto──> [broadcast] ──auto──> [scan]   │
│                                                                         │
│  [scan] ──auto──> [classify] ──auto──> [converge] ──auto──> [respond]  │
│                                                                         │
│  [respond] ──click──> [negotiate] ──auto──> [filter] ──auto──> [deep]  │
│                                                                         │
│  [deep] ──auto──> [proposal] ──click──> [confirm] ──auto──> [history]  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Phase Definitions

### Phase 1: Requirement Launch (launch)
- **Trigger**: User submits requirement
- **Duration**: 800ms
- **Animation**:
  1. Requirement text shrinks to a point (scale 1 -> 0.1)
  2. Point moves to center of screen
  3. Lines shoot outward from the point (8-12 lines, radial)
- **Exit**: Auto-transition to broadcast

### Phase 2: Broadcast Scan (broadcast)
- **Duration**: 2000ms (2-3 wave cycles)
- **Animation**:
  1. Background shows 20-30 faint placeholder circles (opacity 0.1)
  2. Ripple waves expand from center (3 waves, staggered)
  3. Placeholder circles flicker when wave passes (opacity pulse)
- **Exit**: Auto-transition to scan

### Phase 3: Agent Discovery (scan)
- **Duration**: 1500ms
- **Animation**:
  1. After 2-3 scan waves, 7 circles become solid
  2. Solid circles appear at scattered positions
  3. Each circle fades in with scale animation
- **Exit**: Auto-transition to classify

### Phase 4: Agent Classification (classify)
- **Duration**: 1200ms
- **Animation**:
  1. Agents get colored borders:
     - Green (#10B981): Willing to participate (4-5)
     - Red (#EF4444): Not matching (1-2)
     - Gray (#9CA3AF): Observing (1-2)
  2. Color appears with pulse effect
- **Exit**: Auto-transition to converge

### Phase 5: Green Agent Convergence (converge)
- **Duration**: 1500ms
- **Animation**:
  1. Red and gray agents fade out (opacity 0, scale 0.8)
  2. Green agents move to form a circle around center
  3. Circle gradually enlarges
  4. Each agent shows loading animation (...)
- **Exit**: Auto-transition to respond

### Phase 6: Agent Response (respond)
- **Duration**: User-controlled
- **Animation**:
  1. Loading dots animate
  2. One by one, agents show response bubbles
  3. Click agent to see detailed info panel
- **Response Types**:
  - Competition: "I want to compete, here are my conditions"
  - Offer: "I have X, can provide Y, need Z"
  - Suggestion: "You could use XX for this"
- **Exit**: User clicks "Start Negotiation"

### Phase 7: Information Convergence (negotiate)
- **Duration**: 3000ms
- **Animation**:
  1. Information particles flow from agents to center
  2. Visible data stream animation (dots moving along lines)
  3. Center node pulses as it receives data
  4. "Your Agent" processes and proposes
- **Exit**: Auto-transition to filter

### Phase 8: Filtering Disconnect (filter)
- **Duration**: 1500ms
- **Animation**:
  1. Some connection lines turn red
  2. Red lines break with animation
  3. Disconnected agents turn red, then fade out
  4. Remaining agents stay connected
- **Exit**: Auto-transition to deep

### Phase 9: Deep Negotiation (deep)
- **Duration**: 4000ms
- **Animation**:
  1. Remaining agents may have peer-to-peer connections
  2. Two agents' connection line highlights when they "chat"
  3. Chat bubbles appear between them
  4. Information flows back to center
  5. Final proposal emerges
- **Exit**: Auto-transition to proposal

### Phase 10: Proposal Confirmation (proposal)
- **Duration**: User-controlled
- **Animation**:
  1. Cancelled agents disappear
  2. Final agents transition from circle to vertical list
  3. Lines extend upward indicating "notify owners via SecondMe"
  4. Each agent shows their role in the proposal
- **Exit**: User clicks "View History"

### Phase 11: History Record (history)
- **Duration**: User-controlled
- **Content**:
  - Complete timeline of all offers
  - Cancellation reasons
  - Each phase's key information
  - Replay capability

## Component Structure

```
components/experience-v2/
├── NetworkGraphV2/
│   ├── NetworkGraphV2.tsx          # Main orchestrator
│   ├── NetworkGraphV2.module.css   # All animations
│   ├── phases/
│   │   ├── LaunchPhase.tsx         # Phase 1
│   │   ├── BroadcastPhase.tsx      # Phase 2-3
│   │   ├── ClassifyPhase.tsx       # Phase 4
│   │   ├── ConvergePhase.tsx       # Phase 5
│   │   ├── RespondPhase.tsx        # Phase 6
│   │   ├── NegotiatePhase.tsx      # Phase 7-8
│   │   ├── DeepNegotiatePhase.tsx  # Phase 9
│   │   └── ProposalPhase.tsx       # Phase 10
│   ├── components/
│   │   ├── PlaceholderCircle.tsx   # Faint background circles
│   │   ├── AgentNode.tsx           # Agent avatar with states
│   │   ├── ConnectionLine.tsx      # Animated connection lines
│   │   ├── DataParticle.tsx        # Information flow particles
│   │   ├── ResponseBubble.tsx      # Agent response bubbles
│   │   └── CenterNode.tsx          # Central requirement node
│   └── hooks/
│       ├── usePhaseTransition.ts   # Phase state machine
│       └── useAnimationTiming.ts   # Animation orchestration
└── shared/
    └── types.ts                    # Extended types
```

## Animation Timing Chart

```
Time(ms)  0    500   1000  1500  2000  2500  3000  3500  4000  4500  5000
          |     |     |     |     |     |     |     |     |     |     |
Phase 1   [=====]                                                        launch
Phase 2         [===========]                                            broadcast
Phase 3                     [=======]                                    scan
Phase 4                             [=====]                              classify
Phase 5                                   [=======]                      converge
Phase 6                                           [USER CONTROLLED]      respond
Phase 7                                                   [=======]      negotiate
Phase 8                                                         [===]   filter
Phase 9                                                             [===] deep
Phase 10                                                                [USER] proposal
```

## CSS Animation Keyframes

### 1. Requirement Shrink & Launch
```css
@keyframes shrinkToPoint {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(0.1); opacity: 0; }
}

@keyframes launchLines {
  0% { stroke-dashoffset: 100; opacity: 1; }
  100% { stroke-dashoffset: 0; opacity: 0; }
}
```

### 2. Broadcast Waves
```css
@keyframes broadcastWave {
  0% { r: 40; opacity: 0.6; stroke-width: 3; }
  100% { r: 200; opacity: 0; stroke-width: 1; }
}
```

### 3. Placeholder Flicker
```css
@keyframes placeholderFlicker {
  0%, 100% { opacity: 0.08; }
  50% { opacity: 0.2; }
}
```

### 4. Agent Classification Pulse
```css
@keyframes classifyPulse {
  0% { box-shadow: 0 0 0 0 var(--classify-color); }
  50% { box-shadow: 0 0 0 8px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}
```

### 5. Convergence Movement
```css
@keyframes convergeToCircle {
  0% { transform: translate(var(--start-x), var(--start-y)); }
  100% { transform: translate(var(--end-x), var(--end-y)); }
}
```

### 6. Data Flow Particles
```css
@keyframes dataFlow {
  0% { offset-distance: 0%; opacity: 1; }
  100% { offset-distance: 100%; opacity: 0; }
}
```

### 7. Line Break Animation
```css
@keyframes lineBreak {
  0% { stroke-dasharray: 100; stroke: var(--c-primary); }
  50% { stroke-dasharray: 50 10; stroke: #EF4444; }
  100% { stroke-dasharray: 0 100; stroke: #EF4444; }
}
```

### 8. Circle to List Transition
```css
@keyframes circleToList {
  0% { transform: translate(var(--circle-x), var(--circle-y)); }
  100% { transform: translate(0, var(--list-y)); }
}
```

## Accessibility Considerations

1. **prefers-reduced-motion**: All animations respect this media query
2. **Focus states**: All interactive elements have visible focus rings
3. **Color contrast**: Text maintains 4.5:1 ratio minimum
4. **Keyboard navigation**: Tab order follows visual flow
5. **Screen reader**: ARIA labels for all dynamic content

## Responsive Breakpoints

- **Desktop**: 1024px+ (full animation, 400px network container)
- **Tablet**: 768px-1023px (reduced animation, 320px container)
- **Mobile**: <768px (simplified animation, 280px container)

## Performance Optimizations

1. Use `transform` and `opacity` for animations (GPU accelerated)
2. Limit concurrent animations to 2-3 elements
3. Use `will-change` sparingly for known animations
4. Debounce resize handlers
5. Use CSS containment where appropriate
