import type React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { FadeIn, Typewriter } from '../components/AnimatedText';
import {
  BotIcon,
  ExternalLinkIcon,
  ShieldCheckIcon,
  SparklesIcon,
  UserIcon,
} from '../components/Icons';
import {
  COLORS,
  FONTS,
  card,
  glassHeader,
  gradientBg,
  gridLines,
  iconCircle,
  sourceBadge,
} from '../styles';

const MESSAGES = [
  {
    sender: 'user',
    text: 'I need to cancel my subscription and get a refund',
    sentiment: 'urgent',
  },
  {
    sender: 'agent',
    text: "I understand you'd like to cancel and receive a refund. I've found your account — your Pro plan has 12 days remaining. I can process a prorated refund of $24.50 right now. Would you like me to proceed?",
    sources: ['Refund Policy v3.2', 'Billing FAQ'],
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
            position: 'absolute',
            top: 48,
            left: 80,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: COLORS.green,
              boxShadow: `0 0 8px ${COLORS.green}`,
            }}
          />
          <span
            style={{
              fontSize: 16,
              fontFamily: FONTS.mono,
              color: COLORS.textMuted,
              textTransform: 'uppercase',
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
            display: 'flex',
            flexDirection: 'column',
            padding: 0,
            overflow: 'hidden',
            position: 'relative',
            borderColor: `${COLORS.gray700}80`,
          }}
        >
          {/* Glass header — matches ChatWindow.jsx */}
          <div style={glassHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={iconCircle(36)}>
                <SparklesIcon size={18} color={COLORS.white} />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.white }}>
                  Support Assistant
                </div>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.7)' }}>Powered by AI</div>
              </div>
            </div>
          </div>

          {/* Messages area */}
          <div
            style={{
              flex: 1,
              padding: 24,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
              overflowY: 'hidden',
            }}
          >
            {/* User message — gradient bubble with User avatar */}
            <FadeIn startFrame={30} durationFrames={15}>
              <div style={{ display: 'flex', flexDirection: 'row-reverse', gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    backgroundColor: COLORS.brand500,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <UserIcon size={16} color={COLORS.white} />
                </div>
                <div
                  style={{
                    maxWidth: 420,
                    padding: '10px 16px',
                    borderRadius: '18px 18px 4px 18px',
                    background: `linear-gradient(135deg, ${COLORS.brand500}, ${COLORS.brand600})`,
                    color: COLORS.white,
                    fontSize: 14,
                    lineHeight: 1.5,
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                  }}
                >
                  {MESSAGES[0].text}
                </div>
              </div>
            </FadeIn>

            {/* Urgent sentiment badge */}
            <FadeIn startFrame={45} durationFrames={10}>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '4px 12px',
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
                      borderRadius: '50%',
                      backgroundColor: COLORS.red,
                      boxShadow: `0 0 6px ${COLORS.red}`,
                    }}
                  />
                  Urgent Sentiment Detected
                </div>
              </div>
            </FadeIn>

            {/* Typing indicator — bouncing dots matching TypingIndicator */}
            {frame >= 55 && frame < 75 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    background: `linear-gradient(135deg, ${COLORS.brand100}, ${COLORS.brand200})`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <BotIcon size={16} color={COLORS.brand600} />
                </div>
                <div
                  style={{
                    display: 'flex',
                    gap: 4,
                    padding: '12px 16px',
                    backgroundColor: COLORS.bgCardLight,
                    borderRadius: '18px 18px 18px 4px',
                    border: `1px solid ${COLORS.gray700}80`,
                  }}
                >
                  {[0, 1, 2].map((i) => (
                    <div
                      key={`dot-${i}`}
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: COLORS.gray500,
                        opacity: interpolate(
                          ((frame - 55 + i * 5) % 15) / 15,
                          [0, 0.5, 1],
                          [0.3, 1, 0.3],
                        ),
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Agent reply — Bot avatar + bordered bubble */}
            <FadeIn startFrame={75} durationFrames={15}>
              <div style={{ display: 'flex', gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    background: `linear-gradient(135deg, ${COLORS.brand100}, ${COLORS.brand200})`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <BotIcon size={16} color={COLORS.brand600} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', maxWidth: 480 }}>
                  <div
                    style={{
                      padding: '10px 16px',
                      borderRadius: '18px 18px 18px 4px',
                      backgroundColor: COLORS.bgCardLight,
                      border: `1px solid ${COLORS.gray700}80`,
                      fontSize: 14,
                      lineHeight: 1.5,
                      color: COLORS.text,
                      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    }}
                  >
                    <Typewriter text={MESSAGES[1].text} startFrame={80} charsPerFrame={2} />
                  </div>

                  {/* Source citation badges — ExternalLink + [n] */}
                  <FadeIn startFrame={170} durationFrames={15}>
                    <div style={{ display: 'flex', gap: 6, marginTop: 6, marginLeft: 4 }}>
                      {MESSAGES[1].sources?.map((src, i) => (
                        <div key={src} style={sourceBadge}>
                          <ExternalLinkIcon size={10} color={COLORS.brand300} />
                          <span style={{ fontWeight: 700 }}>[{i + 1}]</span>
                          {src}
                        </div>
                      ))}
                    </div>
                  </FadeIn>
                </div>
              </div>
            </FadeIn>
          </div>
        </div>
      </FadeIn>

      {/* Citation popup — ShieldCheck header + ConfidenceMeter */}
      <FadeIn startFrame={195} durationFrames={15}>
        <div
          style={{
            position: 'absolute',
            right: 160,
            top: 280,
            ...card,
            width: 380,
            padding: 20,
            borderColor: COLORS.brand500,
            boxShadow: `0 0 30px ${COLORS.brand500}22, 0 8px 32px rgba(0,0,0,0.4)`,
            backdropFilter: 'blur(12px)',
          }}
        >
          {/* Header with ShieldCheck */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 12,
            }}
          >
            <ShieldCheckIcon size={16} color={COLORS.brand400} />
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.brand400,
                textTransform: 'uppercase',
                letterSpacing: 1,
              }}
            >
              Verified Source
            </span>
          </div>

          {/* Excerpt */}
          <div
            style={{
              borderLeft: `3px solid ${COLORS.brand500}`,
              paddingLeft: 14,
              fontSize: 14,
              color: COLORS.textMuted,
              lineHeight: 1.6,
              fontStyle: 'italic',
              marginBottom: 14,
            }}
          >
            &quot;Prorated refunds are calculated based on remaining days in the billing cycle.
            Process via Billing &rarr; Refunds &rarr; Prorated.&quot;
          </div>

          {/* Confidence meter — progress bar */}
          <div style={{ marginBottom: 10 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 12,
                marginBottom: 4,
              }}
            >
              <span style={{ color: COLORS.textDim, fontWeight: 600 }}>Confidence</span>
              <span style={{ color: COLORS.green, fontWeight: 700 }}>94.2%</span>
            </div>
            <div
              style={{
                height: 6,
                borderRadius: 3,
                backgroundColor: COLORS.gray700,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: '94.2%',
                  height: '100%',
                  borderRadius: 3,
                  background: `linear-gradient(90deg, ${COLORS.green}, ${COLORS.emerald})`,
                }}
              />
            </div>
          </div>

          <div style={{ fontSize: 12, color: COLORS.textDim }}>Updated 2h ago</div>
        </div>
      </FadeIn>
    </div>
  );
};
