# Demo Video (Remotion)

Animated product demo video for Support Intelligence Core, built with [Remotion](https://remotion.dev).

## Scenes

| # | Scene | Duration | What it shows |
|---|-------|----------|---------------|
| 1 | **Hero** | 4s | Title, tagline, tech stack pills, orbiting dots |
| 2 | **Chat Widget** | 8s | Customer message → sentiment detection → agent reply with typewriter → citation popup |
| 3 | **Agent Copilot** | 9s | Chrome extension sidebar on mock helpdesk → context detection → suggested reply → copy to clipboard |
| 4 | **HITL Queue** | 7s | Priority badges, SLA timers, claim → review → approve → "Golden Path Saved" |
| 5 | **Governance** | 7s | Metric cards, SLA compliance, agents table, audit log |
| 6 | **Learning Loop** | 12s | Feedback loop (Pinecone) → Activity Stream (Redis) → Activity Graph (AGE) → Playbook Engine (LangGraph) |
| 7 | **Closing** | 6s | Stats grid, compliance badges, tagline, GitHub CTA |

**Total: ~53 seconds at 30fps, 1920x1080**

## Quick Start

```bash
cd apps/demo-video
npm install

# Open Remotion Studio (live preview)
npx remotion studio

# Render full video
npx remotion render DemoVideo out/demo.mp4

# Render a single scene for preview
npx remotion render Scene6-Learning out/learning.mp4
```

## Available Compositions

- `DemoVideo` — Full video (all 7 scenes)
- `Scene1-Hero` through `Scene7-Closing` — Individual scenes for development

## Project Structure

```
apps/demo-video/
├── src/
│   ├── index.ts              # Remotion entry point
│   ├── DemoVideo.tsx          # Root composition (Series of all scenes)
│   ├── styles.ts              # Design tokens, shared styles
│   ├── components/
│   │   └── AnimatedText.tsx   # Reusable animation primitives
│   └── scenes/
│       ├── Scene1Hero.tsx
│       ├── Scene2ChatWidget.tsx
│       ├── Scene3Copilot.tsx
│       ├── Scene4HITL.tsx
│       ├── Scene5Governance.tsx
│       ├── Scene6Learning.tsx
│       └── Scene7Closing.tsx
├── remotion.config.ts
├── package.json
└── tsconfig.json
```

## Customization

- **Timing:** Adjust `SCENE_DURATIONS` in `DemoVideo.tsx`
- **Colors:** Edit `COLORS` in `styles.ts`
- **Content:** Each scene has mock data at the top of the file — edit directly
- **Add scenes:** Create a new file in `scenes/`, add to `DemoVideo.tsx` Series and register a Composition

## Requirements

- Node.js 18+
- Chrome (for Remotion rendering)
