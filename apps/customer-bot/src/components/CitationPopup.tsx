import React from "react";

export interface CitationPopupProps {
  excerpt: string;
  confidence: number;
  lastUpdated: string;
  sourceUrl?: string;
  onClose: () => void;
}

export default function CitationPopup({ excerpt, confidence, lastUpdated, sourceUrl, onClose }: CitationPopupProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Citation details">
      <div className="bg-white rounded shadow-lg p-6 max-w-md w-full relative">
        <button onClick={onClose} aria-label="Close citation popup" className="absolute top-2 right-2 text-gray-500 hover:text-gray-800 focus:ring-2 focus:ring-blue-400">✕</button>
        <h3 className="text-lg font-bold mb-2">Source Excerpt</h3>
        <blockquote className="italic text-gray-700 border-l-4 border-blue-400 pl-4 mb-3">{excerpt}</blockquote>
        <div className="mb-2 text-sm text-gray-600">Confidence: <span className="font-semibold">{(confidence * 100).toFixed(1)}%</span></div>
        <div className="mb-2 text-sm text-gray-600">Last Updated: <span className="font-semibold">{lastUpdated}</span></div>
        {sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline text-sm">View full source</a>}
      </div>
    </div>
  );
}
