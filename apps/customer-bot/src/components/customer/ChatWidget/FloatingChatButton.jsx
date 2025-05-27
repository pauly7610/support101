import React from 'react';
import { shadows } from '../../../theme';

import PropTypes from 'prop-types';

export default function FloatingChatButton({ onClick }) {
  return (
    <button
      aria-label="Open chat"
      onClick={onClick}
      className="fixed bottom-6 right-6 w-16 h-16 rounded-full flex items-center justify-center shadow-chat-float bg-gradient-to-br from-primary-blue to-primary-blue-dark text-white hover:scale-105 hover:shadow-lg transition-transform animate-pulse-slow z-50"
      style={{ boxShadow: shadows.chatFloat }}
    >
      <svg width="24" height="24" fill="none" viewBox="0 0 24 24">
        <path
          d="M5 19l2.79-2.79A1 1 0 018.53 16H19a1 1 0 001-1V6a1 1 0 00-1-1H5a1 1 0 00-1 1v12a1 1 0 001 1z"
          fill="currentColor"
        />
      </svg>
    </button>
  );
}

FloatingChatButton.propTypes = {
  onClick: PropTypes.func.isRequired,
};
