import React from 'react';

export default function Button({ children, variant = 'primary', ...props }) {
  const base =
    'inline-flex items-center justify-center font-medium rounded px-4 py-2 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  const variants = {
    primary: 'bg-primary-blue text-white hover:bg-primary-blue-dark',
    secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200',
    danger: 'bg-error-red text-white hover:bg-red-700',
    ghost: 'bg-transparent text-primary-blue hover:bg-primary-blue-light',
  };
  return (
    <button className={`${base} ${variants[variant]}`} {...props}>
      {children}
    </button>
  );
}
