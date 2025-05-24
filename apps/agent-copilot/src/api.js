// API utility for backend integration
// Adjust BACKEND_URL if needed (e.g., http://localhost:8000 or from env)
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

/**
 * Generate a suggested reply using the backend RAG endpoint.
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
