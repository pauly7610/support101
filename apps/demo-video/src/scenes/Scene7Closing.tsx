import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { FadeIn, AnimatedText, ScaleIn } from "../components/AnimatedText";
import { COLORS, FONTS, gradientBg, gridLines, heading1, heading2, bodyText } from "../styles";

const STATS = [
  { value: "9", label: "Agent Blueprints", icon: "🤖" },
  { value: "4", label: "Learning Layers", icon: "🧠" },
  { value: "∞", label: "Multi-Tenant", icon: "🏢" },
  { value: "100%", label: "Open Source", icon: "🔓" },
];

const COMPLIANCE = ["GDPR", "CCPA", "SOC2", "HIPAA"];

export const Scene7Closing: React.FC = () => {
  const frame = useCurrentFrame();

  const pulseScale = 1 + Math.sin(frame * 0.08) * 0.02;

  return (
    <div style={gradientBg}>
      <div style={gridLines} />

      {/* Animated glow ring */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: `translate(-50%, -50%) scale(${pulseScale})`,
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${COLORS.primary}08 0%, transparent 70%)`,
          border: `1px solid ${COLORS.primary}15`,
          pointerEvents: "none",
        }}
      />

      {/* Stats grid */}
      <div
        style={{
          display: "flex",
          gap: 32,
          marginBottom: 48,
        }}
      >
        {STATS.map((stat, i) => (
          <ScaleIn key={stat.label} startFrame={5 + i * 10} durationFrames={15}>
            <div
              style={{
                width: 200,
                padding: "28px 24px",
                borderRadius: 16,
                backgroundColor: COLORS.bgCard,
                border: `1px solid ${COLORS.gray700}`,
                textAlign: "center",
                boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
              }}
            >
              <div style={{ fontSize: 36, marginBottom: 8 }}>{stat.icon}</div>
              <div
                style={{
                  fontSize: 40,
                  fontWeight: 800,
                  fontFamily: FONTS.heading,
                  background: `linear-gradient(135deg, ${COLORS.white}, ${COLORS.primaryLight})`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                {stat.value}
              </div>
              <div
                style={{
                  fontSize: 14,
                  color: COLORS.textMuted,
                  marginTop: 4,
                  fontWeight: 500,
                }}
              >
                {stat.label}
              </div>
            </div>
          </ScaleIn>
        ))}
      </div>

      {/* Compliance badges */}
      <FadeIn startFrame={55} durationFrames={20}>
        <div style={{ display: "flex", gap: 12, marginBottom: 40 }}>
          {COMPLIANCE.map((c, i) => (
            <div
              key={c}
              style={{
                padding: "6px 18px",
                borderRadius: 9999,
                backgroundColor: `${COLORS.green}15`,
                border: `1px solid ${COLORS.green}33`,
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.green,
                fontFamily: FONTS.mono,
                opacity: interpolate(
                  frame,
                  [55 + i * 5, 65 + i * 5],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
              }}
            >
              {c}
            </div>
          ))}
        </div>
      </FadeIn>

      {/* Tagline */}
      <AnimatedText
        text="Deploy in minutes. Get smarter forever."
        startFrame={80}
        durationFrames={25}
        style={{
          ...heading2,
          fontSize: 48,
          textAlign: "center",
          background: `linear-gradient(135deg, ${COLORS.white} 0%, ${COLORS.primaryLight} 60%, ${COLORS.accentLight} 100%)`,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          marginBottom: 32,
        }}
      />

      {/* GitHub CTA */}
      <FadeIn startFrame={110} durationFrames={20}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            padding: "16px 32px",
            borderRadius: 12,
            backgroundColor: COLORS.bgCard,
            border: `1px solid ${COLORS.gray600}`,
            boxShadow: `0 4px 20px ${COLORS.primary}22`,
          }}
        >
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill={COLORS.white}
          >
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
          </svg>
          <div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 700,
                color: COLORS.white,
              }}
            >
              github.com/pauly7610/support101
            </div>
            <div style={{ fontSize: 13, color: COLORS.textMuted }}>
              MIT License · Star on GitHub
            </div>
          </div>
        </div>
      </FadeIn>

      {/* Bottom branding */}
      <FadeIn startFrame={130} durationFrames={15}>
        <div
          style={{
            position: "absolute",
            bottom: 48,
            left: 0,
            right: 0,
            textAlign: "center",
            fontSize: 14,
            color: COLORS.textDim,
          }}
        >
          Support Intelligence Core · Built with LangChain, Pinecone, Redis, Apache AGE, LangGraph
        </div>
      </FadeIn>
    </div>
  );
};
