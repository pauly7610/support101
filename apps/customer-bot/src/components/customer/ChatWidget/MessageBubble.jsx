import { Bot, ExternalLink, User } from 'lucide-react';
import { cn } from '../../../lib/utils';

import PropTypes from 'prop-types';

function Avatar({ isUser }) {
  return (
    <div
      className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        isUser
          ? 'bg-brand-500 text-white'
          : 'bg-gradient-to-br from-brand-100 to-brand-200 text-brand-600 dark:from-brand-800 dark:to-brand-900 dark:text-brand-300',
      )}
    >
      {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
    </div>
  );
}

export default function MessageBubble({ from, text, timestamp, sources }) {
  const isUser = from === 'user';
  return (
    <div
      className={cn(
        'flex gap-2.5 mb-3',
        isUser ? 'flex-row-reverse' : 'flex-row',
        isUser ? 'animate-slide-in-right' : 'animate-slide-in-left',
      )}
    >
      <Avatar isUser={isUser} />
      <div className="flex flex-col max-w-[75%]">
        <div
          className={cn(
            'px-4 py-2.5 text-sm leading-relaxed',
            isUser
              ? 'bg-gradient-to-br from-brand-500 to-brand-600 text-white rounded-2xl rounded-tr-md shadow-sm'
              : 'bg-gray-100 dark:bg-slate-800 text-gray-800 dark:text-slate-200 rounded-2xl rounded-tl-md shadow-sm border border-gray-200/50 dark:border-slate-700/50',
          )}
        >
          <div className="whitespace-pre-wrap">{text}</div>
        </div>
        {sources && sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5 px-1">
            {sources.map((s) => (
              <span
                key={s}
                className={cn(
                  'inline-flex items-center gap-1',
                  'text-[10px] font-medium px-2 py-0.5 rounded-full',
                  'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-300',
                  'hover:bg-brand-100 dark:hover:bg-brand-900/50',
                  'cursor-pointer transition-colors',
                )}
              >
                <ExternalLink className="w-2.5 h-2.5" />
                {s}
              </span>
            ))}
          </div>
        )}
        <span
          className={cn(
            'text-[10px] mt-1 px-1',
            isUser
              ? 'text-right text-gray-400 dark:text-slate-500'
              : 'text-gray-400 dark:text-slate-500',
          )}
        >
          {timestamp}
        </span>
      </div>
    </div>
  );
}

MessageBubble.propTypes = {
  from: PropTypes.string.isRequired,
  text: PropTypes.string.isRequired,
  timestamp: PropTypes.string.isRequired,
  sources: PropTypes.arrayOf(PropTypes.string),
};
