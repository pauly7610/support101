import * as idb from 'idb-keyval';
import { AlertTriangle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { cn } from '../lib/utils';

const ESCALATION_LOG_KEY = 'escalation_log';

function groupByDay(escalations: unknown[]) {
  const counts: Record<string, number> = {};
  for (const e of escalations) {
    const escalation = e as { timestamp: number };
    const day = new Date(escalation.timestamp).toLocaleDateString();
    counts[day] = (counts[day] || 0) + 1;
  }
  return Object.entries(counts)
    .sort(([a], [b]) => new Date(a).getTime() - new Date(b).getTime())
    .map(([day, count]) => ({ day, count }));
}

function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={cn('animate-pulse rounded bg-gray-200 dark:bg-slate-700', className)}
      style={style}
    />
  );
}

function ChartSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-5 w-40" />
      <div className="flex items-end gap-2 h-40">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton
            key={`skeleton-${i}`}
            className="w-8"
            style={{ height: `${30 + Math.random() * 90}px` }}
          />
        ))}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div
        className={cn(
          'w-12 h-12 rounded-full flex items-center justify-center mb-3',
          'bg-emerald-50 dark:bg-emerald-900/20',
        )}
      >
        <AlertTriangle className="w-5 h-5 text-emerald-500" />
      </div>
      <p className="text-sm font-medium text-gray-700 dark:text-slate-300">No escalations yet</p>
      <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
        Escalation data will appear here when tickets are flagged
      </p>
    </div>
  );
}

export default function EscalationCharts() {
  const [escalations, setEscalations] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    idb.get(ESCALATION_LOG_KEY).then((log: unknown[] | undefined) => {
      setEscalations(log || []);
      setLoading(false);
    });
  }, []);

  if (loading) return <ChartSkeleton />;

  const data = groupByDay(escalations);

  if (data.length === 0) return <EmptyState />;

  return (
    <div className="mb-8">
      <h3 className="text-sm font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-3">
        Escalations per Day
      </h3>
      <div
        className={cn(
          'rounded-xl p-4',
          'bg-white dark:bg-slate-900',
          'border border-gray-200 dark:border-slate-700',
          'shadow-sm',
        )}
      >
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="currentColor" opacity={0.1} />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 10, fill: '#9ca3af' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 10, fill: '#9ca3af' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: '1px solid #e5e7eb',
                boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                fontSize: 12,
              }}
              labelStyle={{ fontWeight: 600 }}
            />
            <Bar
              dataKey="count"
              name="Escalations"
              fill="#6366f1"
              radius={[4, 4, 0, 0]}
              maxBarSize={32}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
