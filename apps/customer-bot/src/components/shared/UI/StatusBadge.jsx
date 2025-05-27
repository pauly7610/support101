import React from 'react';

const colorMap = {
  success: 'bg-success-green text-white',
  warning: 'bg-warning-orange text-white',
  error: 'bg-error-red text-white',
  info: 'bg-info-cyan text-white',
  default: 'bg-gray-200 text-gray-700',
};

import PropTypes from 'prop-types';

export default function StatusBadge({ status = 'default', children }) {
  return (
    <span
      className={`inline-block px-3 py-1 text-xs rounded-full font-semibold ${
        colorMap[status] || colorMap.default
      }`}
    >
      {children}
    </span>
  );
}

StatusBadge.propTypes = {
  status: PropTypes.string,
  children: PropTypes.node,
};
