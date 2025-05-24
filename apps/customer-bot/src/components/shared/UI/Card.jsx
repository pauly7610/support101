import React from 'react';

export default function Card({ children, className = '', ...props }) {
  return (
    <div className={`bg-white border border-gray-200 rounded-lg shadow-sm p-4 ${className}`} {...props}>
      {children}
    </div>
  );
}
