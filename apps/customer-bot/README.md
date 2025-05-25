# Customer Bot (Next.js Widget)

A Next.js + Tailwind CSS chatbot widget for customer-facing support.

## Features
- Floating chat button and window for customer interaction
- Sends customer questions to backend for RAG-based AI replies
- Displays reply and sources in chat bubbles
- Escalation analytics dashboard with filters (user, date range)
- Advanced analytics visualizations (trend, user breakdown)
- Uses shared design system and UI primitives
- Accessibility compliance (ARIA, keyboard, contrast)

## Accessibility Compliance

### Automated Tests
- Run Cypress accessibility tests with:
  ```bash
  cd apps/customer-bot
  npx cypress run --spec cypress/integration/accessibility_spec.cy.ts
  ```
- Tests use `cypress-axe` to check ARIA labels, keyboard navigation, and color contrast for ChatWidget and AnalyticsDashboard.

### Manual Review
- Use keyboard (Tab, Shift+Tab, Enter, Space) to navigate all interactive elements.
- Check ARIA labels and roles using browser devtools (Accessibility panel).
- Use a screen reader (NVDA, VoiceOver, etc.) to verify all content is accessible.
- Confirm color contrast ratios meet or exceed 4.5:1 (use tools like axe or browser extensions).

## Integration
- Consumes `/generate_reply` endpoint from the backend
- Configure `NEXT_PUBLIC_BACKEND_URL` in `.env` for deployment

## Dev
- `npm install`
- `npm run dev` (with backend running)
