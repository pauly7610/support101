# Support Intelligence Core — Design System

This document describes the design tokens, UI principles, and component usage for the Support Intelligence Core MVP. It is intended to ensure consistency and scalability across all frontend apps.

---

## Design Tokens

Tokens are available in both Tailwind config (`tailwind.config.js`) and as JavaScript constants (`src/theme.js`) in each app.

### Colors
- **Primary Blue:** #2563eb
- **Primary Blue Dark:** #1d4ed8
- **Primary Blue Light:** #3b82f6
- **Status**
  - Success: #10b981
  - Warning: #f59e0b
  - Error: #ef4444
  - Info: #06b6d4
- **Grays:** #f9fafb, #f3f4f6, #e5e7eb, #6b7280, #374151, #111827

### Spacing
- 1: 0.25rem, 2: 0.5rem, 4: 1rem, 6: 1.5rem, 8: 2rem, 12: 3rem

### Typography
- 4xl: 2.25rem, 3xl: 1.875rem, 2xl: 1.5rem, xl: 1.25rem, base: 1rem, sm: 0.875rem, xs: 0.75rem

### Radii
- Chat window: 16px
- Message bubble: 18px

### Shadows
- Chat float: 0 4px 12px rgba(37, 99, 235, 0.3)

### Breakpoints
- sm: 640px, md: 768px, lg: 1024px, xl: 1280px, 2xl: 1536px

---

## Shared UI Primitives

Reusable components for both apps (see `src/components/shared/UI/`):
- **Button**: Primary, secondary, danger, ghost variants
- **Input**: Standard text input
- **Card**: Container for grouping content
- **StatusBadge**: Success, warning, error, info, default

---

## Component Structure

### Customer Bot
- `customer/ChatWidget`: Floating button, chat window, message bubbles
- `customer/HelpCenter`: Help articles, search
- `customer/TicketPortal`: Ticket status and details
- `shared/UI`, `shared/Layout`, `shared/Icons`, `shared/Charts`

### Agent Copilot
- `agent/Dashboard`: Metrics, active tickets
- `agent/ChatInterface`: Three-panel chat
- `agent/Copilot`: AI Copilot sidebar
- `shared/UI`, `shared/Layout`, `shared/Icons`, `shared/Charts`

---

## Best Practices
- Always use design tokens for colors, spacing, and typography.
- Compose UI from shared primitives where possible.
- Keep component logic isolated and reusable.
- Document new components and patterns in this file.

---

For updates, see `tailwind.config.js`, `src/theme.js`, and component READMEs in each app.
