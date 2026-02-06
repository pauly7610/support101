import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { FadeIn, Typewriter } from "../components/AnimatedText";
import { COLORS, FONTS, gradientBg, gridLines, card } from "../styles";

export const Scene3Copilot: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <div style={gradientBg}>
      <div style={gridLines} />

      {/* Section label */}
      <FadeIn startFrame={0} durationFrames={15}>
        <div
          style={{
            position: "absolute",
            top: 48,
            left: 80,
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: COLORS.accent,
              boxShadow: `0 0 8px ${COLORS.accent}`,
            }}
          />
          <span
            style={{
              fontSize: 16,
              fontFamily: FONTS.mono,
              color: COLORS.textMuted,
              textTransform: "uppercase",
              letterSpacing: 2,
            }}
          >
            Agent Copilot — Chrome Extension
          </span>
        </div>
      </FadeIn>

      {/* Mock helpdesk background */}
      <FadeIn startFrame={5} durationFrames={20}>
        <div
          style={{
            position: "absolute",
            left: 80,
            top: 120,
            width: 1040,
            height: 840,
            backgroundColor: "#fafafa",
            borderRadius: 12,
            border: "1px solid #e0e0e0",
            overflow: "hidden",
          }}
        >
          {/* Mock helpdesk header */}
          <div
            style={{
              height: 48,
              backgroundColor: "#1a1a2e",
              display: "flex",
              alignItems: "center",
              padding: "0 20px",
              gap: 12,
            }}
          >
            <div style={{ display: "flex", gap: 6 }}>
              {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
                <div
                  key={c}
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: c,
                  }}
                />
              ))}
            </div>
            <div
              style={{
                flex: 1,
                textAlign: "center",
                fontSize: 13,
                color: "#999",
                fontFamily: FONTS.mono,
              }}
            >
              helpdesk.acme.com/tickets/T-4821
            </div>
          </div>

          {/* Mock ticket content */}
          <div style={{ padding: 32 }}>
            <div
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: "#1a1a1a",
                marginBottom: 8,
              }}
            >
              Ticket #T-4821
            </div>
            <div
              style={{
                display: "inline-block",
                padding: "3px 10px",
                borderRadius: 4,
                backgroundColor: "#fef3c7",
                color: "#92400e",
                fontSize: 12,
                fontWeight: 600,
                marginBottom: 16,
              }}
            >
              Priority: High
            </div>
            <div
              style={{
                fontSize: 15,
                color: "#444",
                lineHeight: 1.7,
                maxWidth: 600,
                marginTop: 12,
              }}
            >
              <strong>Customer:</strong> Sarah M. (Enterprise Plan)
              <br />
              <br />
              "We're seeing intermittent 502 errors on the API gateway since
              yesterday's deployment. Our monitoring shows ~15% of requests
              failing. This is affecting our production environment and we need
              this resolved ASAP."
            </div>
          </div>
        </div>
      </FadeIn>

      {/* Copilot sidebar */}
      <FadeIn startFrame={25} durationFrames={20}>
        <div
          style={{
            position: "absolute",
            right: 0,
            top: 120,
            width: 420,
            height: 840,
            backgroundColor: COLORS.bgCard,
            borderLeft: `1px solid ${COLORS.gray700}`,
            borderRadius: "12px 0 0 12px",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            boxShadow: "-8px 0 32px rgba(0,0,0,0.3)",
          }}
        >
          {/* Sidebar header */}
          <div
            style={{
              padding: "16px 20px",
              borderBottom: `1px solid ${COLORS.gray700}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: `linear-gradient(135deg, ${COLORS.primaryDark}, ${COLORS.primary})`,
            }}
          >
            <span style={{ fontSize: 16, fontWeight: 700, color: COLORS.white }}>
              AI Copilot
            </span>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                backgroundColor: COLORS.green,
                boxShadow: `0 0 8px ${COLORS.green}`,
              }}
            />
          </div>

          {/* Context detected */}
          <FadeIn startFrame={40} durationFrames={15}>
            <div style={{ padding: "16px 20px" }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: COLORS.textDim,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                  marginBottom: 8,
                }}
              >
                Context Detected
              </div>
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  backgroundColor: `${COLORS.accent}15`,
                  border: `1px solid ${COLORS.accent}33`,
                  fontSize: 13,
                  color: COLORS.accentLight,
                }}
              >
                🔗 Ticket #T-4821 · Enterprise · API Issue
              </div>
            </div>
          </FadeIn>

          {/* Suggested reply */}
          <FadeIn startFrame={60} durationFrames={15}>
            <div style={{ padding: "0 20px" }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: COLORS.textDim,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                  marginBottom: 8,
                }}
              >
                Suggested Reply
              </div>
              <div
                style={{
                  padding: 14,
                  borderRadius: 8,
                  backgroundColor: COLORS.bgCardLight,
                  border: `1px solid ${COLORS.gray700}`,
                  fontSize: 14,
                  lineHeight: 1.6,
                  color: COLORS.text,
                }}
              >
                <Typewriter
                  text="Hi Sarah, I've identified the root cause — the 502 errors correlate with the new rate limiter config deployed yesterday. I recommend rolling back the gateway config to v2.3.1 while we patch the threshold values. I can initiate the rollback now if approved."
                  startFrame={65}
                  charsPerFrame={1.8}
                />
              </div>
            </div>
          </FadeIn>

          {/* Sources */}
          <FadeIn startFrame={210} durationFrames={15}>
            <div style={{ padding: "16px 20px" }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: COLORS.textDim,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                  marginBottom: 8,
                }}
              >
                Sources
              </div>
              {[
                { id: 1, title: "API Gateway Runbook", confidence: 96 },
                { id: 2, title: "Deploy Rollback SOP", confidence: 91 },
              ].map((src) => (
                <div
                  key={src.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "8px 12px",
                    borderRadius: 6,
                    backgroundColor: `${COLORS.primary}10`,
                    border: `1px solid ${COLORS.primary}22`,
                    marginBottom: 6,
                    fontSize: 13,
                  }}
                >
                  <span style={{ color: COLORS.primaryLight }}>
                    [{src.id}] {src.title}
                  </span>
                  <span
                    style={{
                      color: COLORS.green,
                      fontWeight: 600,
                      fontSize: 12,
                    }}
                  >
                    {src.confidence}%
                  </span>
                </div>
              ))}
            </div>
          </FadeIn>

          {/* Copy button */}
          <FadeIn startFrame={235} durationFrames={10}>
            <div style={{ padding: "0 20px" }}>
              <div
                style={{
                  padding: "12px 0",
                  borderRadius: 8,
                  background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.primaryDark})`,
                  textAlign: "center",
                  fontSize: 14,
                  fontWeight: 600,
                  color: COLORS.white,
                  cursor: "pointer",
                  boxShadow: `0 4px 12px ${COLORS.primary}44`,
                }}
              >
                {frame >= 250 ? "✓ Copied to Clipboard" : "📋 Copy to Reply"}
              </div>
            </div>
          </FadeIn>
        </div>
      </FadeIn>
    </div>
  );
};
