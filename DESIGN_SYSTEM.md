# Support Intelligence Core — Design System

Design tokens, UI principles, and component patterns for all frontend apps. Ensures consistency across customer-bot, agent-copilot, and admin-dashboard.

---

## Design Tokens

Tokens are defined in each app's `tailwind.config.js` (extended, not overridden). Utility function `cn()` (clsx + tailwind-merge) available in `src/lib/utils.ts`.

### Colors

#### Brand Scale (Primary)
| Token | Value | Usage |
|-------|-------|-------|
| `brand-50` | `#eff6ff` | Lightest background |
| `brand-100` | `#dbeafe` | Hover states |
| `brand-500` | `#2563eb` | Primary actions, buttons |
| `brand-600` | `#1d4ed8` | Hover on primary |
| `brand-700` | `#1e40af` | Active states |
| `brand-900` | `#1e3a5f` | Dark mode accents |

#### Status Colors
- **Success:** `#10b981` (green-500)
- **Warning:** `#f59e0b` (amber-500)
- **Error:** `#ef4444` (red-500)
- **Info:** `#06b6d4` (cyan-500)

#### Dark Mode
Enabled via `darkMode: 'class'`. Dark surfaces use `slate-800`/`slate-900`. CSS variables for light/dark defined in `styles/globals.css`.

### Typography
- Headings: `text-sm font-semibold` (compact UI)
- Body: `text-sm` (14px)
- Captions: `text-xs` (12px), `text-[10px]` for subtitles
- Labels: `text-xs font-semibold uppercase tracking-wider`

### Spacing & Radii
- Cards/inputs: `rounded-xl` (12px)
- Message bubbles: `rounded-2xl` (16px)
- Buttons: `rounded-xl` with `px-4 py-2.5`
- Standard padding: `p-4` (sections), `px-5 py-3.5` (headers)

### Shadows
- **Glass morphism:** `shadow-xl` with `backdrop-blur`
- **Float button:** `shadow-lg shadow-brand-500/25`

### Animations (Tailwind keyframes)
| Name | Usage |
|------|-------|
| `fade-in` | Page/section entry |
| `fade-in-up` | Card/modal entry |
| `slide-in-right` / `slide-in-left` | Sidebar/panel entry |
| `scale-in` | Button/badge pop |
| `bounce-dot` | Typing indicator dots |
| `shimmer` | Skeleton loading |
| `pulse-slow` | Connection status dot |

---

## Icons

All apps use **Lucide React** (`lucide-react`). Common icons:
- `Sparkles` — AI/copilot header
- `MessageCircle` — Chat float button
- `Bot` / `User` — Message avatars
- `Send` — Submit button
- `Search` — Knowledge base search
- `ExternalLink` — Citation links
- `Copy` / `Check` — Copy-to-clipboard feedback
- `Wifi` / `WifiOff` — Connection toast
- `ShieldCheck` — Citation confidence

---

## Component Structure

### Customer Bot (`apps/customer-bot`)
- **FloatingChatButton** — Gradient background, unread badge, Lucide MessageCircle
- **ChatWindow** — Glass header with Sparkles icon, TypingIndicator with bouncing dots
- **MessageBubble** — Bot/User Lucide avatars, gradient user bubbles, citation badges
- **CitationPopup** — ConfidenceMeter progress bar, ShieldCheck header, backdrop blur, click-outside-to-close
- **EscalationCharts** — Recharts bar/line charts with loading skeletons
- **ApprovalQueue** — HITL review queue with priority badges, SLA timers
- **GovernanceDashboard** — Agent metrics, compliance stats, audit log

### Agent Copilot (`apps/agent-copilot`)
- **CopilotSidebar** — Gradient header, ConnectionDot component, copy button with feedback, source badges, KB search with Search icon
- **WebSocketProvider** — Context provider for real-time WebSocket connection with auto-reconnect
- **Toast** — Lucide Wifi/WifiOff icons, rounded design

### Admin Dashboard (`apps/admin-dashboard`)
- **AdminDashboard** — 6-tab layout: Overview, Knowledge Base, Agents, Cost Tracking, Voice I/O, Settings
- **Sidebar navigation** with active tab highlighting
- **Metric cards** with Recharts visualizations
- **Budget alerts** and cost breakdowns

---

## Shared Patterns

### Glass Morphism
```css
.glass { @apply bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-white/20; }
.glass-header { @apply bg-gradient-to-r from-brand-500 to-brand-600; }
```

### `cn()` Utility
```ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
```

### Accessibility
- ARIA labels on all interactive elements (`aria-label`, `data-testid`)
- Keyboard navigation support
- Color contrast ratio >= 4.5:1
- Screen reader compatible (semantic HTML)

---

## Best Practices
- Always use design tokens — never hardcode colors or spacing
- Use `cn()` for conditional/merged class names
- Compose UI from shared patterns
- Use Lucide icons consistently (never mix icon libraries)
- Test components with Vitest + React Testing Library
- Lint with Biome before committing

---

For token definitions, see `tailwind.config.js` and `styles/globals.css` in each app.
