import {
  BarChart3,
  BookOpen,
  Bot,
  DollarSign,
  FileText,
  Mic,
  RefreshCw,
  Settings,
  Shield,
  Upload,
} from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface CostDashboard {
  period: string;
  current_spend_usd: number;
  monthly_budget_usd: number;
  budget_remaining_usd: number;
  budget_utilization_pct: number;
  total_requests: number;
  total_tokens: number;
  avg_cost_per_request_usd: number;
  by_model: Record<string, { requests: number; tokens: number; cost_usd: number }>;
  recent_alerts: Array<{ message: string; percentage: number }>;
}

interface GovernanceData {
  agents: { total: number; active: number; awaiting_human: number };
  hitl: { pending: number; completed: number; expired: number };
  audit: { total_events: number; recent_events: number };
}

interface VoiceStatus {
  enabled: boolean;
  supported_audio_formats: string[];
  supported_voices: string[];
}

type ActiveTab = 'overview' | 'knowledge' | 'agents' | 'costs' | 'voice' | 'settings';

function MetricCard({
  icon: Icon,
  label,
  value,
  subtext,
  color = 'text-gray-900',
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subtext?: string;
  color?: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-gray-50 rounded-lg">
          <Icon className="w-4 h-4 text-gray-500" />
        </div>
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
      </div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      {subtext && <div className="text-xs text-gray-400 mt-1">{subtext}</div>}
    </div>
  );
}

function BudgetBar({ utilization }: { utilization: number }) {
  const color =
    utilization >= 90 ? 'bg-red-500' : utilization >= 70 ? 'bg-yellow-500' : 'bg-green-500';
  return (
    <div className="w-full bg-gray-100 rounded-full h-3">
      <div
        className={`h-3 rounded-full transition-all ${color}`}
        style={{ width: `${Math.min(utilization, 100)}%` }}
      />
    </div>
  );
}

function Sidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
}) {
  const tabs: Array<{ id: ActiveTab; label: string; icon: React.ElementType }> = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
    { id: 'agents', label: 'Agents', icon: Bot },
    { id: 'costs', label: 'Cost Tracking', icon: DollarSign },
    { id: 'voice', label: 'Voice I/O', icon: Mic },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen p-4">
      <div className="flex items-center gap-2 mb-8 px-2">
        <Shield className="w-6 h-6 text-brand-600" />
        <span className="text-lg font-bold text-gray-900">Support101</span>
      </div>
      <nav className="space-y-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-brand-50 text-brand-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}

function OverviewTab({
  costs,
  governance,
}: {
  costs: CostDashboard | null;
  governance: GovernanceData | null;
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Dashboard Overview</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={Bot}
          label="Active Agents"
          value={governance?.agents.active ?? '—'}
          subtext={`${governance?.agents.total ?? 0} total`}
          color="text-brand-600"
        />
        <MetricCard
          icon={Shield}
          label="HITL Pending"
          value={governance?.hitl.pending ?? '—'}
          subtext={`${governance?.hitl.completed ?? 0} completed`}
          color={(governance?.hitl.pending ?? 0) > 5 ? 'text-red-600' : 'text-green-600'}
        />
        <MetricCard
          icon={DollarSign}
          label="Monthly Spend"
          value={costs ? `$${costs.current_spend_usd.toFixed(2)}` : '—'}
          subtext={costs ? `${costs.budget_utilization_pct}% of budget` : undefined}
        />
        <MetricCard
          icon={BarChart3}
          label="API Requests"
          value={costs?.total_requests ?? '—'}
          subtext={costs ? `${costs.total_tokens.toLocaleString()} tokens` : undefined}
        />
      </div>

      {costs && (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">Budget Utilization</h3>
            <span className="text-sm text-gray-500">
              ${costs.budget_remaining_usd.toFixed(2)} remaining
            </span>
          </div>
          <BudgetBar utilization={costs.budget_utilization_pct} />
        </div>
      )}

      {costs && costs.recent_alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-red-800 mb-2">Recent Alerts</h3>
          {costs.recent_alerts.map((alert, i) => (
            <div key={i} className="text-sm text-red-700">
              {alert.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function KnowledgeBaseTab() {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = ['application/pdf', 'text/plain', 'text/markdown'];
    if (!allowed.includes(file.type) && !file.name.endsWith('.md')) {
      setMessage('Only PDF, TXT, and MD files are supported.');
      return;
    }

    setUploading(true);
    setMessage('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${BACKEND_URL}/ingest_documentation`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`Upload failed: HTTP ${res.status}`);
      const data = await res.json();
      setMessage(`Ingested ${data.chunks_created ?? '?'} chunks from "${file.name}".`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Knowledge Base Management</h2>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <Upload className="w-5 h-5 text-brand-600" />
          <h3 className="text-sm font-semibold text-gray-700">Upload Document</h3>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Upload PDF, TXT, or Markdown files to add to the knowledge base. Documents will be
          chunked, embedded, and indexed in Pinecone.
        </p>
        <label className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 cursor-pointer transition-colors">
          <FileText className="w-4 h-4" />
          {uploading ? 'Uploading...' : 'Choose File'}
          <input
            type="file"
            accept=".pdf,.txt,.md"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
        {message && (
          <div className="mt-3 text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{message}</div>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Index Statistics</h3>
        <p className="text-sm text-gray-500">
          Connect to the backend to view Pinecone index stats (total vectors, namespaces, fullness).
        </p>
      </div>
    </div>
  );
}

function AgentsTab({ governance }: { governance: GovernanceData | null }) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Agent Configuration</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          icon={Bot}
          label="Total Agents"
          value={governance?.agents.total ?? '—'}
          color="text-gray-900"
        />
        <MetricCard
          icon={Bot}
          label="Active"
          value={governance?.agents.active ?? '—'}
          color="text-green-600"
        />
        <MetricCard
          icon={Shield}
          label="Awaiting Human"
          value={governance?.agents.awaiting_human ?? '—'}
          color="text-yellow-600"
        />
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Agent Blueprints</h3>
        <p className="text-sm text-gray-500 mb-4">
          Manage agent blueprints, permissions, and execution limits.
        </p>
        <div className="space-y-2">
          {['triage_agent', 'knowledge_manager_agent', 'compliance_auditor_agent'].map((bp) => (
            <div key={bp} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-700">{bp}</span>
              </div>
              <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
                active
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Audit Log</h3>
        <p className="text-sm text-gray-500">
          {governance?.audit.total_events ?? 0} total events ({governance?.audit.recent_events ?? 0}{' '}
          recent)
        </p>
      </div>
    </div>
  );
}

function CostsTab({ costs }: { costs: CostDashboard | null }) {
  if (!costs) {
    return <div className="text-center py-12 text-gray-400">Loading cost data...</div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">LLM Cost Tracking</h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          icon={DollarSign}
          label="Current Spend"
          value={`$${costs.current_spend_usd.toFixed(2)}`}
          subtext={`Period: ${costs.period}`}
          color="text-gray-900"
        />
        <MetricCard
          icon={DollarSign}
          label="Budget"
          value={`$${costs.monthly_budget_usd.toFixed(0)}`}
          subtext={`${costs.budget_utilization_pct}% used`}
        />
        <MetricCard
          icon={BarChart3}
          label="Total Requests"
          value={costs.total_requests.toLocaleString()}
        />
        <MetricCard
          icon={BarChart3}
          label="Avg Cost/Request"
          value={`$${costs.avg_cost_per_request_usd.toFixed(4)}`}
          subtext={`${costs.total_tokens.toLocaleString()} tokens total`}
        />
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Budget Utilization</h3>
        <BudgetBar utilization={costs.budget_utilization_pct} />
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>$0</span>
          <span>${costs.monthly_budget_usd.toFixed(0)}</span>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Cost by Model</h3>
        {Object.keys(costs.by_model).length === 0 ? (
          <p className="text-sm text-gray-400">No usage data yet.</p>
        ) : (
          <div className="space-y-2">
            {Object.entries(costs.by_model).map(([model, data]) => (
              <div
                key={model}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div>
                  <span className="text-sm font-medium text-gray-700">{model}</span>
                  <span className="text-xs text-gray-400 ml-2">
                    {data.requests} requests · {data.tokens.toLocaleString()} tokens
                  </span>
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  ${data.cost_usd.toFixed(4)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function VoiceTab({ voiceStatus }: { voiceStatus: VoiceStatus | null }) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Voice I/O Configuration</h2>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <Mic className="w-5 h-5 text-brand-600" />
          <h3 className="text-sm font-semibold text-gray-700">Voice Status</h3>
          <span
            className={`text-xs px-2 py-1 rounded-full font-medium ${
              voiceStatus?.enabled ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}
          >
            {voiceStatus?.enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>

        {voiceStatus && (
          <div className="space-y-3">
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Supported Audio Formats
              </h4>
              <div className="flex flex-wrap gap-1">
                {voiceStatus.supported_audio_formats.map((fmt) => (
                  <span key={fmt} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                    .{fmt}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Available Voices
              </h4>
              <div className="flex flex-wrap gap-1">
                {voiceStatus.supported_voices.map((v) => (
                  <span key={v} className="text-xs px-2 py-0.5 bg-brand-50 text-brand-700 rounded">
                    {v}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Environment Variables</h3>
        <div className="space-y-2 text-sm">
          {[
            ['VOICE_ENABLED', 'Enable/disable voice features'],
            ['VOICE_STT_MODEL', 'Whisper model (default: whisper-1)'],
            ['VOICE_TTS_MODEL', 'TTS model (default: tts-1)'],
            ['VOICE_TTS_VOICE', 'Default voice (default: nova)'],
            ['VOICE_TTS_SPEED', 'Playback speed 0.25-4.0 (default: 1.0)'],
            ['VOICE_MAX_AUDIO_MB', 'Max upload size (default: 25)'],
          ].map(([key, desc]) => (
            <div key={key} className="flex items-start gap-3 p-2 bg-gray-50 rounded">
              <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded whitespace-nowrap">
                {key}
              </code>
              <span className="text-xs text-gray-500">{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SettingsTab() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Settings</h2>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">API Configuration</h3>
        <div className="space-y-3">
          {[
            ['Backend URL', BACKEND_URL],
            ['A2A Endpoint', `${BACKEND_URL}/a2a`],
            ['Agent Card', `${BACKEND_URL}/.well-known/agent.json`],
            ['WebSocket', `ws://${BACKEND_URL.replace(/^https?:\/\//, '')}/ws/copilot`],
          ].map(([label, url]) => (
            <div
              key={label}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <span className="text-sm text-gray-600">{label}</span>
              <code className="text-xs font-mono text-gray-500">{url}</code>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Feature Flags</h3>
        <div className="space-y-2">
          {[
            ['Voice I/O', true],
            ['Cost Tracking', true],
            ['A2A Protocol', true],
            ['OTEL Tracing', true],
            ['Pinecone Reranking', true],
          ].map(([feature, enabled]) => (
            <div
              key={String(feature)}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <span className="text-sm text-gray-700">{String(feature)}</span>
              <span
                className={`text-xs px-2 py-1 rounded-full font-medium ${
                  enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}
              >
                {enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [costs, setCosts] = useState<CostDashboard | null>(null);
  const [governance, setGovernance] = useState<GovernanceData | null>(null);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [costsRes, govRes, voiceRes] = await Promise.allSettled([
        fetch(`${BACKEND_URL}/v1/analytics/costs`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${BACKEND_URL}/v1/governance/dashboard`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${BACKEND_URL}/v1/voice/status`).then((r) => (r.ok ? r.json() : null)),
      ]);

      if (costsRes.status === 'fulfilled' && costsRes.value) setCosts(costsRes.value);
      if (govRes.status === 'fulfilled' && govRes.value) setGovernance(govRes.value);
      if (voiceRes.status === 'fulfilled' && voiceRes.value) setVoiceStatus(voiceRes.value);
    } catch {
      // Silently handle — dashboard shows placeholder states
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="flex min-h-screen">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
              <p className="text-sm text-gray-500 mt-1">
                Knowledge base, agents, costs, and system configuration
              </p>
            </div>
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {activeTab === 'overview' && <OverviewTab costs={costs} governance={governance} />}
          {activeTab === 'knowledge' && <KnowledgeBaseTab />}
          {activeTab === 'agents' && <AgentsTab governance={governance} />}
          {activeTab === 'costs' && <CostsTab costs={costs} />}
          {activeTab === 'voice' && <VoiceTab voiceStatus={voiceStatus} />}
          {activeTab === 'settings' && <SettingsTab />}
        </div>
      </main>
    </div>
  );
}
