// API utility for backend integration
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

/**
 * Generate a suggested reply from the backend RAG endpoint.
 * @param {Object} ticketContext - The TicketContext object (user_id, ticket_id, content, etc)
 * @returns {Promise<{reply_text: string, sources: Array}>}
 */
export async function generateSuggestedReply(ticketContext) {
  const res = await fetch(`${BACKEND_URL}/generate_reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ticketContext)
  });
  if (!res.ok) throw new Error("Failed to fetch suggested reply");
  return res.json();
}

/**
 * Report an escalation event to the backend analytics endpoint.
 * @param {Object} escalation - { text, timestamp, user_id, ticket_id, ... }
 * @returns {Promise<void>}
 */
export async function reportEscalation(escalation) {
  const res = await fetch(`${BACKEND_URL}/report_escalation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(escalation)
  });
  if (!res.ok) throw new Error("Failed to report escalation");
}
