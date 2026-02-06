import { useCallback, useEffect, useState } from 'react';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface HITLRequest {
  request_id: string;
  agent_id: string;
  tenant_id: string;
  request_type: string;
  priority: string;
  status: string;
  question: string;
  context: Record<string, unknown>;
  options: string[];
  created_at: string;
  assigned_to: string | null;
  sla_deadline: string | null;
}

interface ApprovalQueueProps {
  tenantId?: string;
  reviewerId?: string;
  pollIntervalMs?: number;
}

const priorityConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  critical: { label: 'Critical', color: 'text-red-800', bgColor: 'bg-red-100' },
  high: { label: 'High', color: 'text-orange-800', bgColor: 'bg-orange-100' },
  medium: { label: 'Medium', color: 'text-yellow-800', bgColor: 'bg-yellow-100' },
  low: { label: 'Low', color: 'text-green-800', bgColor: 'bg-green-100' },
};

const statusConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  pending: { label: 'Pending', color: 'text-blue-800', bgColor: 'bg-blue-100' },
  assigned: { label: 'Assigned', color: 'text-purple-800', bgColor: 'bg-purple-100' },
  in_progress: { label: 'In Progress', color: 'text-indigo-800', bgColor: 'bg-indigo-100' },
  completed: { label: 'Completed', color: 'text-green-800', bgColor: 'bg-green-100' },
  expired: { label: 'Expired', color: 'text-gray-800', bgColor: 'bg-gray-100' },
};

function Badge({ type, value }: { type: 'priority' | 'status'; value: string }) {
  const config =
    type === 'priority'
      ? priorityConfig[value] || priorityConfig.medium
      : statusConfig[value] || statusConfig.pending;
  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs font-semibold rounded-full ${config.bgColor} ${config.color}`}
    >
      {config.label}
    </span>
  );
}

function TimeAgo({ dateStr }: { dateStr: string }) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return <span className="text-xs text-gray-500">just now</span>;
  if (minutes < 60) return <span className="text-xs text-gray-500">{minutes}m ago</span>;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return <span className="text-xs text-gray-500">{hours}h ago</span>;
  const days = Math.floor(hours / 24);
  return <span className="text-xs text-gray-500">{days}d ago</span>;
}

function SLAIndicator({ deadline }: { deadline: string | null }) {
  if (!deadline) return null;
  const remaining = new Date(deadline).getTime() - Date.now();
  const minutes = Math.floor(remaining / 60000);
  if (minutes < 0)
    return (
      <span className="text-xs font-semibold text-red-600" role="alert" aria-label="SLA breached">
        SLA Breached
      </span>
    );
  if (minutes < 15)
    return (
      <span className="text-xs font-semibold text-orange-600" aria-label="SLA at risk">
        {minutes}m left
      </span>
    );
  return (
    <span className="text-xs text-gray-500" aria-label={`${minutes} minutes until SLA deadline`}>
      {minutes}m left
    </span>
  );
}

export default function ApprovalQueue({
  tenantId,
  reviewerId = 'current-user',
  pollIntervalMs = 10000,
}: ApprovalQueueProps) {
  const [requests, setRequests] = useState<HITLRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<HITLRequest | null>(null);
  const [responseText, setResponseText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending' | 'assigned'>('all');

  const fetchRequests = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (tenantId) params.set('tenant_id', tenantId);
      const res = await fetch(`${BACKEND_URL}/v1/hitl/queue?${params.toString()}`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: HITLRequest[] = await res.json();
      setRequests(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch requests');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    fetchRequests();
    const interval = setInterval(fetchRequests, pollIntervalMs);
    return () => clearInterval(interval);
  }, [fetchRequests, pollIntervalMs]);

  const handleAssign = async (requestId: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/v1/hitl/queue/${requestId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewer_id: reviewerId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign request');
    }
  };

  const handleRespond = async (requestId: string, decision: string) => {
    setSubmitting(true);
    try {
      const res = await fetch(`${BACKEND_URL}/v1/hitl/queue/${requestId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: reviewerId,
          decision,
          notes: responseText,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSelectedRequest(null);
      setResponseText('');
      await fetchRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit response');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredRequests = requests.filter((r) => {
    if (filter === 'pending') return r.status === 'pending';
    if (filter === 'assigned') return r.status === 'assigned' && r.assigned_to === reviewerId;
    return true;
  });

  const pendingCount = requests.filter((r) => r.status === 'pending').length;
  const assignedCount = requests.filter(
    (r) => r.status === 'assigned' && r.assigned_to === reviewerId,
  ).length;
  const breachedCount = requests.filter(
    (r) => r.sla_deadline && new Date(r.sla_deadline).getTime() < Date.now(),
  ).length;

  return (
    <main className="max-w-4xl mx-auto my-8" aria-label="Approval Queue">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Approval Queue</h1>
        <p className="text-sm text-gray-500 mt-1">Human-in-the-loop requests requiring review</p>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
          <div className="text-2xl font-bold text-blue-600">{pendingCount}</div>
          <div className="text-xs text-gray-500 mt-1">Pending Review</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
          <div className="text-2xl font-bold text-purple-600">{assignedCount}</div>
          <div className="text-xs text-gray-500 mt-1">Assigned to You</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
          <div
            className={`text-2xl font-bold ${breachedCount > 0 ? 'text-red-600' : 'text-green-600'}`}
          >
            {breachedCount}
          </div>
          <div className="text-xs text-gray-500 mt-1">SLA Breached</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div
        className="flex gap-1 mb-4 border-b border-gray-200"
        role="tablist"
        aria-label="Filter requests"
      >
        {(['all', 'pending', 'assigned'] as const).map((tab) => (
          <button
            type="button"
            key={tab}
            role="tab"
            aria-selected={filter === tab}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filter === tab
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            onClick={() => setFilter(tab)}
          >
            {tab === 'all' ? 'All' : tab === 'pending' ? 'Pending' : 'My Assignments'}
            {tab === 'pending' && pendingCount > 0 && (
              <span className="ml-1.5 inline-block px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Error Banner */}
      {error && (
        <div
          className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
          role="alert"
        >
          {error}
          <button
            type="button"
            className="ml-2 underline text-red-800 hover:text-red-900"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12 text-gray-400" aria-live="polite">
          Loading requests...
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredRequests.length === 0 && (
        <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
          <div className="text-4xl mb-3">&#9745;</div>
          <div className="text-gray-500 text-sm">No requests matching this filter</div>
        </div>
      )}

      {/* Request List */}
      <ul className="space-y-3 list-none" aria-label="HITL requests">
        {filteredRequests.map((req) => (
          <li
            key={req.request_id}
            className={`bg-white border rounded-lg shadow-sm transition-all ${
              selectedRequest?.request_id === req.request_id
                ? 'border-blue-400 ring-2 ring-blue-100'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            {/* Request Header */}
            <div className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <Badge type="priority" value={req.priority} />
                    <Badge type="status" value={req.status} />
                    <SLAIndicator deadline={req.sla_deadline} />
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 truncate">{req.question}</h3>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                    <span>Agent: {req.agent_id.slice(0, 8)}...</span>
                    <span>Type: {req.request_type}</span>
                    <TimeAgo dateStr={req.created_at} />
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 flex-shrink-0">
                  {req.status === 'pending' && (
                    <button
                      type="button"
                      className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
                      onClick={() => handleAssign(req.request_id)}
                      aria-label={`Assign request ${req.request_id} to yourself`}
                    >
                      Claim
                    </button>
                  )}
                  {req.status === 'assigned' && req.assigned_to === reviewerId && (
                    <button
                      type="button"
                      className="px-3 py-1.5 text-xs font-medium bg-purple-600 text-white rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-1"
                      onClick={() =>
                        setSelectedRequest(
                          selectedRequest?.request_id === req.request_id ? null : req,
                        )
                      }
                      aria-label={`Review request ${req.request_id}`}
                    >
                      {selectedRequest?.request_id === req.request_id ? 'Close' : 'Review'}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Expanded Review Panel */}
            {selectedRequest?.request_id === req.request_id && (
              <div className="border-t border-gray-100 p-4 bg-gray-50">
                {/* Context */}
                <div className="mb-4">
                  <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                    Context
                  </h4>
                  <pre className="text-xs bg-white border border-gray-200 rounded p-3 overflow-x-auto max-h-48">
                    {JSON.stringify(req.context, null, 2)}
                  </pre>
                </div>

                {/* Response Options */}
                {req.options && req.options.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                      Decision
                    </h4>
                    <div className="flex gap-2 flex-wrap">
                      {req.options.map((option) => (
                        <button
                          type="button"
                          key={option}
                          className="px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-md bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:opacity-50"
                          onClick={() => handleRespond(req.request_id, option)}
                          disabled={submitting}
                          aria-label={`Choose ${option}`}
                        >
                          {option.replace(/_/g, ' ')}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Notes */}
                <div className="mb-3">
                  <label
                    htmlFor={`notes-${req.request_id}`}
                    className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-1 block"
                  >
                    Notes (optional)
                  </label>
                  <textarea
                    id={`notes-${req.request_id}`}
                    className="w-full border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={2}
                    value={responseText}
                    onChange={(e) => setResponseText(e.target.value)}
                    placeholder="Add review notes..."
                    aria-label="Review notes"
                  />
                </div>

                {/* Quick Approve/Reject */}
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="px-4 py-2 text-sm font-medium bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1 disabled:opacity-50"
                    onClick={() => handleRespond(req.request_id, 'approve')}
                    disabled={submitting}
                    aria-label="Approve request"
                  >
                    {submitting ? 'Submitting...' : 'Approve'}
                  </button>
                  <button
                    type="button"
                    className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 disabled:opacity-50"
                    onClick={() => handleRespond(req.request_id, 'reject')}
                    disabled={submitting}
                    aria-label="Reject request"
                  >
                    Reject
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
