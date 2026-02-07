import { Clock, ExternalLink, ShieldCheck, X } from 'lucide-react';
import { cn } from '../lib/utils';

export interface CitationPopupProps {
  excerpt: string;
  confidence: number;
  lastUpdated: string;
  sourceUrl?: string;
  onClose?: () => void;
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500';
  const textColor =
    pct >= 80
      ? 'text-emerald-600 dark:text-emerald-400'
      : pct >= 60
        ? 'text-amber-600 dark:text-amber-400'
        : 'text-red-600 dark:text-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-500', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn('text-xs font-semibold tabular-nums', textColor)}>{pct}%</span>
    </div>
  );
}

export default function CitationPopup({
  excerpt,
  confidence,
  lastUpdated,
  sourceUrl,
  onClose,
}: CitationPopupProps) {
  return (
    <dialog
      open
      data-testid="citation-backdrop"
      className="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in"
      aria-modal="true"
      aria-label="Citation details"
      onClick={(e) => e.target === e.currentTarget && onClose?.()}
      onKeyDown={(e) => e.key === 'Escape' && onClose?.()}
    >
      <div
        className={cn(
          'bg-white dark:bg-slate-900',
          'rounded-2xl shadow-2xl',
          'p-6 max-w-md w-full mx-4',
          'border border-gray-200/50 dark:border-slate-700/50',
          'animate-scale-in',
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-brand-500" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">
              Source Citation
            </h3>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close citation popup"
              className={cn(
                'w-7 h-7 rounded-lg flex items-center justify-center',
                'text-gray-400 hover:text-gray-600 hover:bg-gray-100',
                'dark:text-slate-500 dark:hover:text-slate-300 dark:hover:bg-slate-800',
                'transition-colors focus:outline-none focus:ring-2 focus:ring-brand-400',
              )}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Excerpt */}
        <blockquote
          className={cn(
            'text-sm text-gray-700 dark:text-slate-300 leading-relaxed',
            'border-l-2 border-brand-400 pl-3 mb-4',
            'italic',
          )}
        >
          {excerpt}
        </blockquote>

        {/* Confidence */}
        <div className="mb-3">
          <span className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider">
            Confidence
          </span>
          <div className="mt-1">
            <ConfidenceMeter value={confidence} />
          </div>
        </div>

        {/* Meta row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-slate-500">
            <Clock className="w-3 h-3" />
            <span>{lastUpdated}</span>
          </div>
          {sourceUrl && (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'inline-flex items-center gap-1',
                'text-xs font-medium px-2.5 py-1 rounded-lg',
                'text-brand-600 bg-brand-50 hover:bg-brand-100',
                'dark:text-brand-300 dark:bg-brand-900/30 dark:hover:bg-brand-900/50',
                'transition-colors',
              )}
            >
              <ExternalLink className="w-3 h-3" />
              View source
            </a>
          )}
        </div>
      </div>
    </dialog>
  );
}
