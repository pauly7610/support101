import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { FadeIn, Typewriter } from "../components/AnimatedText";
import { COLORS, FONTS, gradientBg, gridLines, card, heading2, bodyText } from "../styles";

const MESSAGES = [
  {
    sender: "user",
    text: "I need to cancel my subscription and get a refund",
    sentiment: "urgent",
  },
  {
    sender: "agent",
    text: "I understand you'd like to cancel and receive a refund. I've found your account — your Pro plan has 12 days remaining. I can process a prorated refund of $24.50 right now. Would you like me to proceed?",
    sources: ["Refund Policy v3.2", "Billing FAQ"],
  },
];

export const Scene2ChatWidget: React.FC = () => {
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
              backgroundColor: COLORS.green,
              boxShadow: `0 0 8px ${COLORS.green}`,
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
            Customer Chat Widget
          </span>
        </div>
      </FadeIn>

      {/* Chat window */}
      <FadeIn startFrame={10} durationFrames={20}>
        <div
          style={{
            ...card,
            width: 680,
            height: 620,
            display: "flex",
            flexDirection: "column",
            padding: 0,
            overflow: "hidden",
            position: "relative",
          }}
        >
          {/* Chat header */}
          <div
            style={{
              padding: "16px 24px",
              borderBottom: `1px solid ${COLORS.gray700}`,
              display: "flex",
              alignItems: "center",
              gap: 12,
              backgroundColor: COLORS.bgCardLight,
            }}
          >
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.accent})`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
              }}
            >
              🤖
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Support Bot</div>
              <div style={{ fontSize: 12, color: COLORS.green }}>● Online</div>
            </div>
          </div>

          {/* Messages area */}
          <div
            style={{
              flex: 1,
              padding: 24,
              display: "flex",
              flexDirection: "column",
              gap: 16,
              overflowY: "hidden",
            }}
          >
            {/* User message */}
            <FadeIn startFrame={30} durationFrames={15}>
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <div
                  style={{
                    maxWidth: 420,
                    padding: "12px 18px",
                    borderRadius: "18px 18px 4px 18px",
                    backgroundColor: COLORS.primary,
                    color: COLORS.white,
                    fontSize: 15,
                    lineHeight: 1.5,
                  }}
                >
                  {MESSAGES[0].text}
                </div>
              </div>
            </FadeIn>

            {/* Urgent sentiment badge */}
            <FadeIn startFrame={45} durationFrames={10}>
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 12px",
                    borderRadius: 9999,
                    backgroundColor: `${COLORS.red}22`,
                    border: `1px solid ${COLORS.red}44`,
                    fontSize: 12,
                    fontWeight: 600,
                    color: COLORS.red,
                  }}
                >
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      backgroundColor: COLORS.red,
                      boxShadow: `0 0 6px ${COLORS.red}`,
                    }}
                  />
                  Urgent Sentiment Detected
                </div>
              </div>
            </FadeIn>

            {/* Typing indicator */}
            {frame >= 55 && frame < 75 && (
              <div style={{ display: "flex", gap: 4, padding: "8px 0" }}>
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      backgroundColor: COLORS.gray500,
                      opacity: interpolate(
                        ((frame - 55 + i * 5) % 15) / 15,
                        [0, 0.5, 1],
                        [0.3, 1, 0.3]
                      ),
                    }}
                  />
                ))}
              </div>
            )}

            {/* Agent reply */}
            <FadeIn startFrame={75} durationFrames={15}>
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div
                  style={{
                    maxWidth: 480,
                    padding: "12px 18px",
                    borderRadius: "18px 18px 18px 4px",
                    backgroundColor: COLORS.bgCardLight,
                    border: `1px solid ${COLORS.gray700}`,
                    fontSize: 15,
                    lineHeight: 1.5,
                    color: COLORS.text,
                  }}
                >
                  <Typewriter
                    text={MESSAGES[1].text}
                    startFrame={80}
                    charsPerFrame={2}
                  />
                </div>
              </div>
            </FadeIn>

            {/* Source citations */}
            <FadeIn startFrame={170} durationFrames={15}>
              <div style={{ display: "flex", gap: 8, marginLeft: 4 }}>
                {MESSAGES[1].sources!.map((src, i) => (
                  <div
                    key={src}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "6px 14px",
                      borderRadius: 8,
                      backgroundColor: `${COLORS.primary}15`,
                      border: `1px solid ${COLORS.primary}33`,
                      fontSize: 13,
                      color: COLORS.primaryLight,
                      fontWeight: 500,
                      cursor: "pointer",
                    }}
                  >
                    <span style={{ fontWeight: 700 }}>[{i + 1}]</span>
                    {src}
                  </div>
                ))}
              </div>
            </FadeIn>
          </div>
        </div>
      </FadeIn>

      {/* Citation popup */}
      <FadeIn startFrame={195} durationFrames={15}>
        <div
          style={{
            position: "absolute",
            right: 160,
            top: 280,
            ...card,
            width: 380,
            padding: 20,
            borderColor: COLORS.primary,
            boxShadow: `0 0 30px ${COLORS.primary}22, 0 8px 32px rgba(0,0,0,0.4)`,
          }}
        >
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: COLORS.primaryLight,
              marginBottom: 8,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            Source Citation
          </div>
          <div
            style={{
              borderLeft: `3px solid ${COLORS.primary}`,
              paddingLeft: 14,
              fontSize: 14,
              color: COLORS.textMuted,
              lineHeight: 1.6,
              fontStyle: "italic",
              marginBottom: 12,
            }}
          >
            "Prorated refunds are calculated based on remaining days in the
            billing cycle. Process via Billing → Refunds → Prorated."
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
            <span style={{ color: COLORS.green, fontWeight: 600 }}>
              Confidence: 94.2%
            </span>
            <span style={{ color: COLORS.textDim }}>Updated 2h ago</span>
          </div>
        </div>
      </FadeIn>
    </div>
  );
};
