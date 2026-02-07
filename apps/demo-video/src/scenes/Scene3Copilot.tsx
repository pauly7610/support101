import type React from 'react';
import { useCurrentFrame } from 'remotion';
import { FadeIn, Typewriter } from '../components/AnimatedText';
import {
  CheckIcon,
  CopyIcon,
  ExternalLinkIcon,
  FileTextIcon,
  SearchIcon,
  SendIcon,
  SparklesIcon,
} from '../components/Icons';
import {
  COLORS,
  FONTS,
  glassHeader,
  gradientBg,
  gridLines,
  iconCircle,
  sourceBadge,
} from '../styles';

const SOURCES = [
  { id: 1, title: 'API Gateway Runbook', confidence: 96 },
  { id: 2, title: 'Deploy Rollback SOP', confidence: 91 },
];

export const Scene3Copilot: React.FC = () => {
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
              backgroundColor: COLORS.accent,
              boxShadow: `0 0 8px ${COLORS.accent}`,
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
            Agent Copilot — Chrome Extension
          </span>
        </div>
      </FadeIn>

      {/* Mock helpdesk background */}
      <FadeIn startFrame={5} durationFrames={20}>
        <div
          style={{
            position: 'absolute',
            left: 80,
            top: 100,
            width: 1420,
            height: 960,
            backgroundColor: '#fafafa',
            borderRadius: 12,
            border: '1px solid #e0e0e0',
            overflow: 'hidden',
          }}
        >
          {/* Mock helpdesk header */}
          <div
            style={{
              height: 48,
              backgroundColor: '#1a1a2e',
              display: 'flex',
              alignItems: 'center',
              padding: '0 20px',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', gap: 6 }}>
              {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
                <div
                  key={c}
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor: c,
                  }}
                />
              ))}
            </div>
            <div
              style={{
                flex: 1,
                textAlign: 'center',
                fontSize: 13,
                color: '#999',
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
                color: '#1a1a1a',
                marginBottom: 8,
              }}
            >
              Ticket #T-4821
            </div>
            <div
              style={{
                display: 'inline-block',
                padding: '3px 10px',
                borderRadius: 4,
                backgroundColor: '#fef3c7',
                color: '#92400e',
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
                color: '#444',
                lineHeight: 1.7,
                maxWidth: 600,
                marginTop: 12,
              }}
            >
              <strong>Customer:</strong> Sarah M. (Enterprise Plan)
              <br />
              <br />
              &quot;We&apos;re seeing intermittent 502 errors on the API gateway since
              yesterday&apos;s deployment. Our monitoring shows ~15% of requests failing. This is
              affecting our production environment and we need this resolved ASAP.&quot;
            </div>
          </div>
        </div>
      </FadeIn>

      {/* Copilot sidebar — matches CopilotSidebar.jsx */}
      <FadeIn startFrame={25} durationFrames={20}>
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: 100,
            width: 420,
            height: 960,
            backgroundColor: COLORS.bgCard,
            borderLeft: `1px solid ${COLORS.gray700}`,
            borderRadius: '12px 0 0 12px',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '-8px 0 32px rgba(0,0,0,0.3)',
          }}
        >
          {/* Glass header with Sparkles + ConnectionDot */}
          <div style={glassHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={iconCircle(32)}>
                <SparklesIcon size={16} color={COLORS.white} />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.white }}>AI Copilot</div>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.6)' }}>
                  Context-aware assistance
                </div>
              </div>
            </div>
            {/* ConnectionDot — emerald with ring */}
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: COLORS.emerald,
                boxShadow: `0 0 6px ${COLORS.emerald}, 0 0 0 3px rgba(255,255,255,0.3)`,
              }}
            />
          </div>

          {/* Context detected */}
          <FadeIn startFrame={40} durationFrames={15}>
            <div style={{ padding: '16px 20px' }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: COLORS.textDim,
                  textTransform: 'uppercase',
                  letterSpacing: 1,
                  marginBottom: 8,
                }}
              >
                Context Detected
              </div>
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: 12,
                  backgroundColor: `${COLORS.accent}15`,
                  border: `1px solid ${COLORS.accent}33`,
                  fontSize: 13,
                  color: COLORS.accentLight,
                }}
              >
                Ticket #T-4821 · Enterprise · API Issue
              </div>
            </div>
          </FadeIn>

          {/* Suggested reply with Copy button */}
          <FadeIn startFrame={60} durationFrames={15}>
            <div style={{ padding: '0 20px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 8,
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: COLORS.textDim,
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                  }}
                >
                  Suggested Reply
                </span>
                {/* Copy → Check feedback button */}
                {frame >= 235 && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '3px 10px',
                      borderRadius: 8,
                      fontSize: 11,
                      fontWeight: 600,
                      backgroundColor: frame >= 250 ? `${COLORS.emerald}22` : COLORS.bgCardLight,
                      color: frame >= 250 ? COLORS.emerald : COLORS.textMuted,
                      border: `1px solid ${frame >= 250 ? `${COLORS.emerald}44` : COLORS.gray700}`,
                    }}
                  >
                    {frame >= 250 ? (
                      <>
                        <CheckIcon size={12} color={COLORS.emerald} /> Copied
                      </>
                    ) : (
                      <>
                        <CopyIcon size={12} color={COLORS.textMuted} /> Copy
                      </>
                    )}
                  </div>
                )}
              </div>
              <div
                style={{
                  padding: 14,
                  borderRadius: 12,
                  backgroundColor: COLORS.bgCardLight,
                  border: `1px solid ${COLORS.gray700}`,
                  fontSize: 14,
                  lineHeight: 1.6,
                  color: COLORS.text,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                }}
              >
                <Typewriter
                  text="Hi Sarah, I've identified the root cause — the 502 errors correlate with the new rate limiter config deployed yesterday. I recommend rolling back the gateway config to v2.3.1 while we patch the threshold values. I can initiate the rollback now if approved."
                  startFrame={65}
                  charsPerFrame={1.8}
                />
              </div>

              {/* Source badges — ExternalLink style */}
              <FadeIn startFrame={210} durationFrames={15}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                  {SOURCES.map((src) => (
                    <div key={src.title} style={sourceBadge}>
                      <ExternalLinkIcon size={10} color={COLORS.brand300} />[{src.id}] {src.title}
                      <span style={{ color: COLORS.green, marginLeft: 4 }}>{src.confidence}%</span>
                    </div>
                  ))}
                </div>
              </FadeIn>
            </div>
          </FadeIn>

          {/* Knowledge Base search — Search icon */}
          <FadeIn startFrame={225} durationFrames={15}>
            <div style={{ padding: '16px 20px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  marginBottom: 8,
                }}
              >
                <FileTextIcon size={14} color={COLORS.textDim} />
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: COLORS.textDim,
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                  }}
                >
                  Knowledge Base
                </span>
              </div>
              <div
                style={{
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <div style={{ position: 'absolute', left: 12 }}>
                  <SearchIcon size={14} color={COLORS.textDim} />
                </div>
                <div
                  style={{
                    width: '100%',
                    padding: '10px 14px 10px 36',
                    borderRadius: 12,
                    backgroundColor: COLORS.bgCardLight,
                    border: `1px solid ${COLORS.gray700}`,
                    fontSize: 13,
                    color: COLORS.textDim,
                  }}
                >
                  Search knowledge base...
                </div>
              </div>
            </div>
          </FadeIn>

          {/* Suggest Reply button — Send icon */}
          <FadeIn startFrame={235} durationFrames={10}>
            <div style={{ padding: '0 20px' }}>
              <div
                style={{
                  padding: '10px 0',
                  borderRadius: 12,
                  background: `linear-gradient(135deg, ${COLORS.brand500}, ${COLORS.brand600})`,
                  textAlign: 'center',
                  fontSize: 14,
                  fontWeight: 600,
                  color: COLORS.white,
                  cursor: 'pointer',
                  boxShadow: `0 4px 12px ${COLORS.brand500}44`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                <SendIcon size={14} color={COLORS.white} />
                Suggest Reply
              </div>
            </div>
          </FadeIn>
        </div>
      </FadeIn>
    </div>
  );
};
