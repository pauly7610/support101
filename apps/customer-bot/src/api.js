// API utility for backend integration
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

/**
 * Generate a suggested reply from the backend RAG endpoint.
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
 * Report an escalation event to the backend analytics endpoint.
 * @param {Object} escalation - { text, timestamp, user_id, ticket_id, ... }
 * @returns {Promise<void>}
 */
export async function reportEscalation(escalation) {
  const res = await fetch(`${BACKEND_URL}/report_escalation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(escalation),
  });
  if (!res.ok) throw new Error('Failed to report escalation');
}

/**
 * Request GDPR-compliant data deletion for the current user.
 * @param {string} user_id
 * @returns {Promise<{status: string}>}
 */
export async function requestGdprDelete(user_id, token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BACKEND_URL}/v1/compliance/gdpr_delete`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ user_id }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to request GDPR deletion');
  }
  return res.json();
}

/**
 * Request CCPA opt-out for the current user.
 * @param {string} user_id
 * @returns {Promise<{status: string}>}
 */
export async function requestCcpaOptout(user_id, token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BACKEND_URL}/v1/compliance/ccpa_optout`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ user_id }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to request CCPA opt-out');
  }
  return res.json();
}
