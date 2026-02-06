// API utility for backend integration
// Adjust BACKEND_URL if needed (e.g., http://localhost:8000 or from env)
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

/**
 * Generate a suggested reply using the backend RAG endpoint.
 * @param {Object} ticketContext - The TicketContext object (user_id, ticket_id, content, etc)
 * @returns {Promise<{reply_text: string, sources: Array}>}
 */
export async function generateSuggestedReply(ticketContext) {
  const res = await fetch(`${BACKEND_URL}/generate_reply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ticketContext),
  });
  if (!res.ok) throw new Error('Failed to fetch suggested reply');
  return res.json();
}

/**
 * Admin: GDPR delete a user by ID (admin only)
 * @param {string} user_id
 * @returns {Promise<{status: string}>}
 */
export async function adminGdprDelete(user_id) {
  const res = await fetch(`${BACKEND_URL}/gdpr_delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id }),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete user data');
  }
  return res.json();
}

/**
 * Fetch escalation analytics (main endpoint, with optional filters)
 * @param {Object} params - { user_id, start_time, end_time }
 * @returns {Promise<{escalations: Array, timeframe: string}>}
 */
export async function getEscalationAnalytics(params = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${BACKEND_URL}/v1/analytics/escalations${q ? `?${q}` : ''}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch escalation analytics');
  return res.json();
}

/**
 * Fetch escalation analytics aggregated by agent
 * @param {Object} params - { agent_id, start_time, end_time }
 * @returns {Promise<{by_agent: Array, filters: Object}>}
 */
export async function getEscalationsByAgent(params = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${BACKEND_URL}/v1/analytics/escalations/by-agent${q ? `?${q}` : ''}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch escalations by agent');
  return res.json();
}

/**
 * Fetch escalation analytics aggregated by category
 * @param {Object} params - { category, start_time, end_time }
 * @returns {Promise<{by_category: Array, filters: Object}>}
 */
export async function getEscalationsByCategory(params = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(
    `${BACKEND_URL}/v1/analytics/escalations/by-category${q ? `?${q}` : ''}`,
    {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    },
  );
  if (!res.ok) throw new Error('Failed to fetch escalations by category');
  return res.json();
}
