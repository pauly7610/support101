import React from 'react';

export default function Input(props) {
  return (
    <input
      className="border border-gray-200 rounded px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-primary-blue"
      {...props}
    />
  );
}
