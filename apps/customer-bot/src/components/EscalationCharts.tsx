import React, { useEffect, useState } from 'react';
import * as idb from 'idb-keyval';

const ESCALATION_LOG_KEY = 'escalation_log';

// Simple bar chart for escalations per day
function groupByDay(escalations: unknown[]) {
  const counts: Record<string, number> = {};
  escalations.forEach((e) => {
    const escalation = e as { timestamp: string };
    const day = new Date(escalation.timestamp).toLocaleDateString();
    counts[day] = (counts[day] || 0) + 1;
  });
  return counts;
}

export default function EscalationCharts() {
  const [escalations, setEscalations] = useState([]);

  useEffect(() => {
    idb.get(ESCALATION_LOG_KEY).then((log: unknown[] = []) => setEscalations(log));
  }, []);

  const counts = groupByDay(escalations);
  const days = Object.keys(counts).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());
  const values = days.map((day) => counts[day]);
  const max = Math.max(...values, 1);

  return (
    <div className="mb-8">
      <h3 className="text-lg font-semibold mb-2">Escalations per Day</h3>
      <div className="flex items-end gap-2 h-40">
        {days.map((day, i) => (
          <div key={day} className="flex flex-col items-center" style={{ width: 36 }}>
            <div
              style={{
                height: `${(values[i] / max) * 120}px`,
                background: '#2563eb',
                width: 24,
                borderRadius: 4,
              }}
              title={`${values[i]} escalation${values[i] !== 1 ? 's' : ''}`}
            ></div>
            <span
              className="text-xs mt-1"
              style={{ writingMode: 'vertical-lr', textOrientation: 'mixed', color: '#555' }}
            >
              {day}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
