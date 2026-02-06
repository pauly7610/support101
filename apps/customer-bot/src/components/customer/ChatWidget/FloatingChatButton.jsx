import { MessageCircle } from 'lucide-react';
import { cn } from '../../../lib/utils';

import PropTypes from 'prop-types';

export default function FloatingChatButton({ onClick, unreadCount = 0 }) {
  return (
    <button
      aria-label={unreadCount > 0 ? `Open chat (${unreadCount} unread)` : 'Open chat'}
      onClick={onClick}
      className={cn(
        'fixed bottom-6 right-6 z-50',
        'w-14 h-14 rounded-full',
        'flex items-center justify-center',
        'bg-gradient-to-br from-brand-500 to-brand-700',
        'text-white shadow-chat-float',
        'hover:scale-110 hover:shadow-glow',
        'active:scale-95',
        'transition-all duration-200 ease-out',
        'focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2',
        'dark:from-brand-400 dark:to-brand-600 dark:focus:ring-offset-slate-900',
      )}
    >
      <MessageCircle className="w-6 h-6" strokeWidth={2} />
      {unreadCount > 0 && (
        <span
          className={cn(
            'absolute -top-1 -right-1',
            'min-w-[20px] h-5 px-1.5',
            'flex items-center justify-center',
            'bg-red-500 text-white text-xs font-bold rounded-full',
            'animate-scale-in',
            'ring-2 ring-white dark:ring-slate-900',
          )}
        >
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      )}
    </button>
  );
}

FloatingChatButton.propTypes = {
  onClick: PropTypes.func.isRequired,
  unreadCount: PropTypes.number,
};
