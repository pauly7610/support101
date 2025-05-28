import React, { useEffect, useState } from 'react';
import Card from './shared/UI/Card';
import { getEscalationAnalytics, getEscalationsByAgent, getEscalationsByCategory } from '../api';

// Design tokens from DESIGN_SYSTEM.md
const PRIMARY_BLUE = '#2563eb';
const GRAY_BG = '#f9fafb';

export default function AnalyticsDashboard() {
  const [main, setMain] = useState({ escalations: [], timeframe: '' });
  const [byAgent, setByAgent] = useState([]);
  const [byCategory, setByCategory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({ agent_id: '', category: '', start_time: '', end_time: '' });

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getEscalationAnalytics({
        user_id: filters.agent_id,
        start_time: filters.start_time,
        end_time: filters.end_time,
      }),
      getEscalationsByAgent({
        agent_id: filters.agent_id,
        start_time: filters.start_time,
        end_time: filters.end_time,
      }),
      getEscalationsByCategory({
        category: filters.category,
        start_time: filters.start_time,
        end_time: filters.end_time,
      }),
    ])
      .then(([main, agent, category]) => {
        setMain(main);
        setByAgent(agent.by_agent || []);
        setByCategory(category.by_category || []);
        setError('');
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters]);

  function handleInput(e) {
    setFilters(f => ({ ...f, [e.target.name]: e.target.value }));
  }

  return (
    <div className="p-8" style={{ background: GRAY_BG, minHeight: '100vh' }}>
      <h1 className="text-3xl font-bold mb-6" style={{ color: PRIMARY_BLUE }}>Escalation Analytics</h1>
      <Card className="mb-6">
        <form className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Agent ID</label>
            <input
              type="text"
              name="agent_id"
              value={filters.agent_id}
              onChange={handleInput}
              className="border rounded px-2 py-1 text-sm w-48"
              placeholder="Agent UUID"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <input
              type="text"
              name="category"
              value={filters.category}
              onChange={handleInput}
              className="border rounded px-2 py-1 text-sm w-48"
              placeholder="Escalation Category"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Time (Unix)</label>
            <input
              type="number"
              name="start_time"
              value={filters.start_time}
              onChange={handleInput}
              className="border rounded px-2 py-1 text-sm w-36"
              placeholder="Start timestamp"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">End Time (Unix)</label>
            <input
              type="number"
              name="end_time"
              value={filters.end_time}
              onChange={handleInput}
              className="border rounded px-2 py-1 text-sm w-36"
              placeholder="End timestamp"
            />
          </div>
        </form>
      </Card>
      {error && <div className="text-red-600 mb-4">{error}</div>}
      {loading ? (
        <div className="text-gray-700">Loading analytics...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Card>
            <h2 className="text-xl font-semibold mb-2" style={{ color: PRIMARY_BLUE }}>Summary</h2>
            <div className="mb-2 text-sm text-gray-600">Timeframe: {main.timeframe}</div>
            <div className="text-3xl font-bold mb-2">{main.escalations.reduce((sum, e) => sum + (e.total_escalations || 0), 0)}</div>
            <div className="text-sm text-gray-500">Total Escalations</div>
            <div className="mt-2 text-sm text-gray-700">Avg. Response Time: {main.escalations.length > 0 ? (main.escalations[0].avg_response_time || 0).toFixed(2) : '--'}s</div>
          </Card>
          <Card>
            <h2 className="text-xl font-semibold mb-2" style={{ color: PRIMARY_BLUE }}>By Agent</h2>
            <ul>
              {byAgent.length === 0 && <li className="text-gray-500">No data</li>}
              {byAgent.map(agent => (
                <li key={agent.agent_id} className="mb-2 flex justify-between items-center">
                  <span className="font-mono text-xs">{agent.agent_id}</span>
                  <span className="ml-2 font-semibold">{agent.total_escalations}</span>
                  <span className="ml-2 text-xs text-gray-500">Avg: {agent.avg_response_time?.toFixed(2) || '--'}s</span>
                </li>
              ))}
            </ul>
          </Card>
          <Card>
            <h2 className="text-xl font-semibold mb-2" style={{ color: PRIMARY_BLUE }}>By Category</h2>
            <ul>
              {byCategory.length === 0 && <li className="text-gray-500">No data</li>}
              {byCategory.map(cat => (
                <li key={cat.category} className="mb-2 flex justify-between items-center">
                  <span className="font-mono text-xs">{cat.category}</span>
                  <span className="ml-2 font-semibold">{cat.total_escalations}</span>
                  <span className="ml-2 text-xs text-gray-500">Avg: {cat.avg_response_time?.toFixed(2) || '--'}s</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </div>
  );
}
