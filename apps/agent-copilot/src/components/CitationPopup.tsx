import React from "react";

interface CitationPopupProps {
  excerpt: string;
  confidence: number; // 0.0 - 1.0
  lastUpdated: string; // ISO date
  sourceUrl?: string;
}

/**
 * Accessible popup for citation details.
 * - Excerpt of source document
 * - Confidence score (as %)
 * - Last updated timestamp
 * - ARIA, keyboard, color contrast ≥4.5:1
 */
const CitationPopup: React.FC<CitationPopupProps> = ({ excerpt, confidence, lastUpdated, sourceUrl }) => {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Citation details"
      tabIndex={0}
      style={{
        background: "#fff",
        color: "#1a1a1a",
        border: "2px solid #333",
        borderRadius: 8,
        boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
        padding: 16,
        minWidth: 320,
        maxWidth: 400,
        outline: "none"
      }}
    >
      <div style={{ marginBottom: 12 }}>
        <strong>Excerpt:</strong>
        <div style={{ fontSize: 15, marginTop: 4, color: "#222" }}>{excerpt}</div>
      </div>
      <div style={{ marginBottom: 8 }}>
        <strong>Confidence:</strong> <span aria-live="polite">{Math.round(confidence * 100)}%</span>
      </div>
      <div style={{ marginBottom: 8 }}>
        <strong>Last updated:</strong> <span>{new Date(lastUpdated).toLocaleString()}</span>
      </div>
      {sourceUrl && (
        <div>
          <a href={sourceUrl} target="_blank" rel="noopener noreferrer" style={{ color: "#0050b3", textDecoration: "underline" }}>
            View source
          </a>
        </div>
      )}
    </div>
  );
};

export default CitationPopup;
