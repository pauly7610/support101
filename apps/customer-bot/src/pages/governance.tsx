import React, { useCallback, useEffect, useState } from 'react';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface AgentSummary {
  total: number;
  active: number;
  awaiting_human: number;
}

interface HITLStats {
  pending: number;
  assigned: number;
  completed: number;
  expired: number;
  avg_response_time_ms: number | null;
}

interface AuditStats {
  total_events: number;
  recent_events: number;
}

interface DashboardData {
  agents: AgentSummary;
  hitl: HITLStats;
  audit: AuditStats;
  tenants: {
    total: number;
    active: number;
  } | null;
}

interface AuditEvent {
  event_id: string;
  event_type: string;
  agent_id: string;
  tenant_id: string;
  timestamp: string;
  details: Record<string, unknown>;
}

interface ActiveAgent {
  agent_id: string;
  name: string;
  blueprint: string;
  status: string;
  tenant_id: string;
}

function MetricCard({
  label,
  value,
  subtext,
  color = 'text-gray-900',
}: {
  label: string;
  value: string | number;
  subtext?: string;
  color?: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
      {subtext && <div className="text-xs text-gray-400 mt-1">{subtext}</div>}
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: 'bg-green-500',
    idle: 'bg-gray-400',
    awaiting_human: 'bg-yellow-500',
    failed: 'bg-red-500',
    completed: 'bg-blue-500',
  };
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${colors[status] || 'bg-gray-400'}`}
      aria-label={`Status: ${status}`}
    />
  );
}

function SeverityBadge({ type }: { type: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    execution_started: { bg: 'bg-blue-100', text: 'text-blue-800' },
    execution_completed: { bg: 'bg-green-100', text: 'text-green-800' },
    execution_failed: { bg: 'bg-red-100', text: 'text-red-800' },
    execution_timeout: { bg: 'bg-orange-100', text: 'text-orange-800' },
    human_feedback_provided: { bg: 'bg-purple-100', text: 'text-purple-800' },
    permission_changed: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    agent_created: { bg: 'bg-teal-100', text: 'text-teal-800' },
  };
  const c = config[type] || { bg: 'bg-gray-100', text: 'text-gray-800' };
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-semibold rounded-full ${c.bg} ${c.text}`}>
      {type.replace(/_/g, ' ')}
    </span>
  );
}

export default function GovernanceDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [agents, setAgents] = useState<ActiveAgent[]>([]);
  const [auditLog, setAuditLog] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'agents' | 'audit'>('overview');

  const fetchDashboard = useCallback(async () => {
    try {
      const [dashRes, agentsRes, auditRes] = await Promise.all([
        fetch(`${BACKEND_URL}/v1/governance/dashboard`, {
          headers: { 'Content-Type': 'application/json' },
        }),
        fetch(`${BACKEND_URL}/v1/governance/agents`, {
          headers: { 'Content-Type': 'application/json' },
        }),
        fetch(`${BACKEND_URL}/v1/governance/audit?limit=20`, {
          headers: { 'Content-Type': 'application/json' },
        }),
      ]);

      if (!dashRes.ok) throw new Error(`Dashboard: HTTP ${dashRes.status}`);
      if (!agentsRes.ok) throw new Error(`Agents: HTTP ${agentsRes.status}`);
      if (!auditRes.ok) throw new Error(`Audit: HTTP ${auditRes.status}`);

      const [dashData, agentsData, auditData] = await Promise.all([
        dashRes.json(),
        agentsRes.json(),
        auditRes.json(),
      ]);

      setDashboard(dashData);
      setAgents(Array.isArray(agentsData) ? agentsData : []);
      setAuditLog(Array.isArray(auditData) ? auditData : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 15000);
    return () => clearInterval(interval);
  }, [fetchDashboard]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto my-8 text-center py-20 text-gray-400" aria-live="polite">
        Loading governance dashboard...
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto my-8" role="main" aria-label="Governance Dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Governance Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Agent monitoring, compliance, and audit trail
          </p>
        </div>
        <button
          className="px-3 py-1.5 text-sm font-medium bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400"
          onClick={fetchDashboard}
          aria-label="Refresh dashboard"
        >
          Refresh
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
          role="alert"
        >
          {error}
          <button
            className="ml-2 underline text-red-800 hover:text-red-900"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Metrics Grid */}
      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard
            label="Total Agents"
            value={dashboard.agents.total}
            subtext={`${dashboard.agents.active} active`}
          />
          <MetricCard
            label="Awaiting Human"
            value={dashboard.agents.awaiting_human}
            color={dashboard.agents.awaiting_human > 0 ? 'text-yellow-600' : 'text-green-600'}
          />
          <MetricCard
            label="HITL Pending"
            value={dashboard.hitl.pending}
            color={dashboard.hitl.pending > 5 ? 'text-red-600' : 'text-blue-600'}
            subtext={`${dashboard.hitl.completed} completed`}
          />
          <MetricCard
            label="Audit Events"
            value={dashboard.audit.total_events}
            subtext={`${dashboard.audit.recent_events} recent`}
          />
        </div>
      )}

      {/* HITL Response Time */}
      {dashboard?.hitl.avg_response_time_ms != null && (
        <div className="mb-6 bg-white border border-gray-200 rounded-lg shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Avg HITL Response Time
              </div>
              <div className="text-xl font-bold text-gray-900 mt-1">
                {(dashboard.hitl.avg_response_time_ms / 1000).toFixed(1)}s
              </div>
            </div>
            <div className="flex gap-4 text-sm text-gray-500">
              <div>
                <span className="font-semibold text-green-600">{dashboard.hitl.completed}</span>{' '}
                resolved
              </div>
              <div>
                <span className="font-semibold text-red-600">{dashboard.hitl.expired}</span>{' '}
                expired
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200" role="tablist" aria-label="Dashboard sections">
        {(['overview', 'agents', 'audit'] as const).map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors capitalize ${
              activeTab === tab
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && dashboard && (
        <div className="space-y-4">
          {/* Tenant Info */}
          {dashboard.tenants && (
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Tenant Overview</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500">Total Tenants</div>
                  <div className="text-lg font-bold">{dashboard.tenants.total}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Active Tenants</div>
                  <div className="text-lg font-bold text-green-600">
                    {dashboard.tenants.active}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SLA Compliance */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">SLA Compliance</h3>
            {dashboard.hitl.expired > 0 ? (
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-full bg-red-500" />
                <span className="text-sm text-red-700 font-medium">
                  {dashboard.hitl.expired} SLA violation{dashboard.hitl.expired !== 1 ? 's' : ''}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-full bg-green-500" />
                <span className="text-sm text-green-700 font-medium">All SLAs met</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Agents Tab */}
      {activeTab === 'agents' && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          {agents.length === 0 ? (
            <div className="text-center py-12 text-gray-400 text-sm">No agents registered</div>
          ) : (
            <table className="w-full text-sm" role="table" aria-label="Active agents">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Agent
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Blueprint
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Status
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Tenant
                  </th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <tr
                    key={agent.agent_id}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{agent.name}</div>
                      <div className="text-xs text-gray-400">{agent.agent_id.slice(0, 12)}...</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-block px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded">
                        {agent.blueprint}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <StatusDot status={agent.status} />
                        <span className="text-gray-700">{agent.status.replace(/_/g, ' ')}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{agent.tenant_id.slice(0, 8)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Audit Tab */}
      {activeTab === 'audit' && (
        <div className="space-y-2" role="log" aria-label="Audit log">
          {auditLog.length === 0 ? (
            <div className="text-center py-12 bg-white border border-gray-200 rounded-lg text-gray-400 text-sm">
              No audit events
            </div>
          ) : (
            auditLog.map((event) => (
              <div
                key={event.event_id}
                className="bg-white border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <SeverityBadge type={event.event_type} />
                      <span className="text-xs text-gray-400">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      Agent: {event.agent_id.slice(0, 12)}...
                      {event.tenant_id && (
                        <span className="ml-2">Tenant: {event.tenant_id.slice(0, 8)}...</span>
                      )}
                    </div>
                  </div>
                  <button
                    className="text-xs text-blue-600 hover:text-blue-800 flex-shrink-0"
                    onClick={() => {
                      const el = document.getElementById(`detail-${event.event_id}`);
                      if (el) el.classList.toggle('hidden');
                    }}
                    aria-label="Toggle event details"
                  >
                    Details
                  </button>
                </div>
                <pre
                  id={`detail-${event.event_id}`}
                  className="hidden mt-2 text-xs bg-gray-50 border border-gray-100 rounded p-2 overflow-x-auto max-h-32"
                >
                  {JSON.stringify(event.details, null, 2)}
                </pre>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
