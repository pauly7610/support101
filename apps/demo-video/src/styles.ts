import { CSSProperties } from "react";

// ── Design Tokens ────────────────────────────────────────────
export const COLORS = {
  bg: "#0a0e1a",
  bgCard: "#111827",
  bgCardLight: "#1f2937",
  primary: "#3b82f6",
  primaryLight: "#60a5fa",
  primaryDark: "#1d4ed8",
  accent: "#8b5cf6",
  accentLight: "#a78bfa",
  green: "#22c55e",
  greenLight: "#4ade80",
  red: "#ef4444",
  orange: "#f97316",
  yellow: "#eab308",
  white: "#ffffff",
  gray100: "#f3f4f6",
  gray200: "#e5e7eb",
  gray300: "#d1d5db",
  gray400: "#9ca3af",
  gray500: "#6b7280",
  gray600: "#4b5563",
  gray700: "#374151",
  gray800: "#1f2937",
  gray900: "#111827",
  text: "#f9fafb",
  textMuted: "#9ca3af",
  textDim: "#6b7280",
};

export const FONTS = {
  heading: "'Inter', 'SF Pro Display', -apple-system, sans-serif",
  body: "'Inter', 'SF Pro Text', -apple-system, sans-serif",
  mono: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
};

// ── Shared Styles ────────────────────────────────────────────
export const fullScreen: CSSProperties = {
  width: 1920,
  height: 1080,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  backgroundColor: COLORS.bg,
  fontFamily: FONTS.body,
  color: COLORS.text,
  overflow: "hidden",
  position: "relative",
};

export const gradientBg: CSSProperties = {
  ...fullScreen,
  background: `radial-gradient(ellipse at 30% 20%, ${COLORS.primaryDark}22 0%, transparent 50%),
               radial-gradient(ellipse at 70% 80%, ${COLORS.accent}15 0%, transparent 50%),
               ${COLORS.bg}`,
};

export const card: CSSProperties = {
  backgroundColor: COLORS.bgCard,
  borderRadius: 16,
  border: `1px solid ${COLORS.gray700}`,
  padding: 24,
  boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
};

export const badge = (color: string, bg: string): CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  padding: "4px 12px",
  borderRadius: 9999,
  fontSize: 13,
  fontWeight: 600,
  color,
  backgroundColor: bg,
});

export const heading1: CSSProperties = {
  fontSize: 64,
  fontWeight: 800,
  fontFamily: FONTS.heading,
  lineHeight: 1.1,
  letterSpacing: -1,
};

export const heading2: CSSProperties = {
  fontSize: 42,
  fontWeight: 700,
  fontFamily: FONTS.heading,
  lineHeight: 1.2,
};

export const heading3: CSSProperties = {
  fontSize: 28,
  fontWeight: 600,
  fontFamily: FONTS.heading,
  lineHeight: 1.3,
};

export const bodyText: CSSProperties = {
  fontSize: 20,
  fontWeight: 400,
  lineHeight: 1.6,
  color: COLORS.textMuted,
};

export const monoText: CSSProperties = {
  fontFamily: FONTS.mono,
  fontSize: 14,
  color: COLORS.primaryLight,
};

export const glowDot = (color: string, size = 12): CSSProperties => ({
  width: size,
  height: size,
  borderRadius: "50%",
  backgroundColor: color,
  boxShadow: `0 0 ${size}px ${color}, 0 0 ${size * 2}px ${color}44`,
});

export const gridLines: CSSProperties = {
  position: "absolute",
  inset: 0,
  backgroundImage: `linear-gradient(${COLORS.gray700}15 1px, transparent 1px),
                     linear-gradient(90deg, ${COLORS.gray700}15 1px, transparent 1px)`,
  backgroundSize: "60px 60px",
  pointerEvents: "none",
};
