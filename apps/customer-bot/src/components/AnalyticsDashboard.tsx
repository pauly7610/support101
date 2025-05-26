import React, { useEffect, useState } from 'react';

interface Escalation {
  id: number;
  user_id: string;
  text: string;
  timestamp: number;
  last_updated: string;
  confidence?: number;
  source_url?: string;
}

interface AnalyticsData {
  total_escalations: number;
  per_day: Record<string, number>;
  last_escalation: Escalation | null;
}

export default function AnalyticsDashboard() {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [feedbackSent, setFeedbackSent] = useState(false);

  async function handleFeedbackSubmit(event: SubmitEvent) {
    event.preventDefault();
    await fetch('/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback }),
    });
    setFeedbackSent(true);
    setTimeout(() => {
      setShowFeedback(false);
      setFeedbackSent(false);
      setFeedback('');
    }, 2000);
  }

  const [userId, setUserId] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [trend, setTrend] = useState<number[]>([]);
  const [trendLabels, setTrendLabels] = useState<string[]>([]);
  const [userBreakdown, setUserBreakdown] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    let polling: ReturnType<typeof setInterval> | undefined = undefined;
    let loading = false;
    async function pollAnalytics() {
      if (!isMounted || loading) return;
      loading = true;
      await fetchAnalytics();
      loading = false;
    }
    pollAnalytics();
    polling = setInterval(pollAnalytics, 10000); // 10s
    return () => {
      isMounted = false;
      clearInterval(polling);
    };
    // eslint-disable-next-line
  }, []);

  async function fetchAnalytics() {
    setLoading(true);
    let url = '/analytics/escalations';
    const params: Record<string, string> = {};
    if (userId) params.user_id = userId;
    if (startDate) params.start_time = `${new Date(startDate).getTime() / 1000}`;
    if (endDate) params.end_time = `${new Date(endDate).getTime() / 1000}`;
    const qs = Object.keys(params)
      .map((k) => `${k}=${encodeURIComponent(params[k])}`)
      .join('&');
    if (qs) url += `?${qs}`;
    const res = await fetch(url);
    const data: AnalyticsData = await res.json();
    setAnalytics(data);
    // Build trend and user breakdown
    if (data.per_day) {
      const days = Object.keys(data.per_day).sort();
      setTrendLabels(days);
      setTrend(days.map((d) => data.per_day[d]));
    }
    // For user breakdown, fetch all (no filter) and count by user_id
    const allRes = await fetch('/analytics/escalations');
    const allData: AnalyticsData = await allRes.json();
    const userCounts: Record<string, number> = {};
    if (allData.last_escalation) {
      // Only one escalation, single user
      userCounts[allData.last_escalation.user_id] = 1;
    } else if (allData.per_day) {
      // For demo, we don't have all escalations, so skip
    }
    setUserBreakdown(userCounts);
    setLoading(false);
  }

  return (
    <>
      <div className="max-w-lg mx-auto my-10 bg-white rounded shadow p-6">
        <h2 className="text-xl font-bold mb-4">Escalation Analytics</h2>
        {/* Filters and dashboard UI */}
        <form
          className="flex gap-2 mb-4 items-end flex-wrap"
          onSubmit={(e) => {
            e.preventDefault();
            fetchAnalytics();
          }}
        >
          <div>
            <label className="block text-xs mb-1">User ID</label>
            <input
              className="border px-2 py-1 rounded text-sm"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="user id"
            />
          </div>
          <div>
            <label className="block text-xs mb-1">Start Date</label>
            <input
              type="date"
              className="border px-2 py-1 rounded text-sm"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs mb-1">End Date</label>
            <input
              type="date"
              className="border px-2 py-1 rounded text-sm"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            Filter
          </button>
        </form>
        {/* Add your stats, charts, etc. here */}
        {loading ? (
          <div>Loading...</div>
        ) : (
          <>
            <div className="mb-4">
              Total Escalations: <b>{analytics?.total_escalations ?? 0}</b>
            </div>
            <div className="mb-6">
              <h3 className="text-md font-semibold mb-2">Escalation Trend</h3>
              <div className="flex items-end gap-2 h-32">
                {trendLabels.map((day, i) => (
                  <div key={day} className="flex flex-col items-center" style={{ width: 28 }}>
                    <div
                      style={{
                        height: `${(trend[i] / Math.max(...trend, 1)) * 80}px`,
                        background: '#2563eb',
                        width: 16,
                        borderRadius: 4,
                      }}
                      title={`${trend[i]} escalation${trend[i] !== 1 ? 's' : ''}`}
                    ></div>
                    <span className="text-xs mt-1" style={{ color: '#555' }}>
                      {day.slice(5)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="mb-6">
              <h3 className="text-md font-semibold mb-2">User Breakdown</h3>
              <div className="flex items-center gap-4">
                {Object.keys(userBreakdown).length === 0 && (
                  <span className="text-gray-400">No data</span>
                )}
                {Object.entries(userBreakdown).map(([user, count]) => (
                  <div key={user} className="flex flex-col items-center">
                    <div
                      className="rounded-full bg-blue-200"
                      style={{
                        width: 48,
                        height: 48,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: 18,
                        color: '#1e40af',
                      }}
                    >
                      {user.slice(0, 2).toUpperCase()}
                    </div>
                    <span className="text-xs mt-1">{user}</span>
                    <span className="text-xs font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            {analytics && analytics.last_escalation && (
              <div className="mb-4 p-3 bg-gray-100 rounded">
                <div className="text-xs text-gray-500 mb-1">Last Escalation</div>
                <div className="text-sm font-semibold">{analytics.last_escalation.text}</div>
                <div className="text-xs text-gray-500">
                  User: {analytics.last_escalation.user_id} |{' '}
                  {new Date(analytics.last_escalation.timestamp * 1000).toLocaleString()}
                </div>
              </div>
            )}
          </>
        )}
      </div>
      {/* Floating Feedback Button */}
      <button
        className="fixed bottom-8 right-8 z-50 bg-blue-600 text-white px-4 py-2 rounded-full shadow-lg hover:bg-blue-700 focus:outline-none focus:ring"
        aria-label="Send Feedback"
        onClick={() => setShowFeedback(true)}
      >
        Send Feedback
      </button>
      {/* Feedback Modal */}
      {showFeedback && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-2">Send Feedback</h3>
            {feedbackSent ? (
              <div className="text-green-600">Thank you for your feedback!</div>
            ) : (
              <form onSubmit={handleFeedbackSubmit}>
                <textarea
                  className="w-full border rounded p-2 mb-3 dark:bg-gray-800 dark:text-white"
                  rows={4}
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Your feedback or issue..."
                  aria-label="Feedback textarea"
                  required
                />
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    className="px-4 py-2 rounded bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600"
                    onClick={() => setShowFeedback(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
                  >
                    Submit
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
