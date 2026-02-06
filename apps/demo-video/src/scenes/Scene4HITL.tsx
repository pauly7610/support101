import type React from 'react';
import { useCurrentFrame } from 'remotion';
import { FadeIn } from '../components/AnimatedText';
import { COLORS, FONTS, badge, card, gradientBg, gridLines } from '../styles';

const REQUESTS = [
  {
    id: 'REQ-7291',
    agent: 'SupportAgent',
    action: 'Process refund $24.50',
    priority: 'critical',
    sla: '4m left',
    slaColor: COLORS.orange,
  },
  {
    id: 'REQ-7290',
    agent: 'TriageAgent',
    action: 'Escalate to L2 Engineering',
    priority: 'high',
    sla: '12m left',
    slaColor: COLORS.textDim,
  },
  {
    id: 'REQ-7289',
    agent: 'OnboardingAgent',
    action: 'Send welcome package',
    priority: 'medium',
    sla: '28m left',
    slaColor: COLORS.textDim,
  },
];

const PRIORITY_COLORS: Record<string, { text: string; bg: string }> = {
  critical: { text: '#fca5a5', bg: '#7f1d1d' },
  high: { text: '#fdba74', bg: '#7c2d12' },
  medium: { text: '#fde68a', bg: '#713f12' },
  low: { text: '#86efac', bg: '#14532d' },
};

export const Scene4HITL: React.FC = () => {
  const frame = useCurrentFrame();

  const selectedIdx = frame >= 80 ? 0 : -1;
  const showApprove = frame >= 120;
  const approved = frame >= 160;
  const showGoldenPath = frame >= 185;

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
              backgroundColor: COLORS.yellow,
              boxShadow: `0 0 8px ${COLORS.yellow}`,
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
            Human-in-the-Loop Approval Queue
          </span>
        </div>
      </FadeIn>

      {/* Queue panel */}
      <div
        style={{
          position: 'absolute',
          left: 80,
          top: 130,
          width: 860,
          display: 'flex',
          flexDirection: 'column',
          gap: 0,
        }}
      >
        {/* Queue header */}
        <FadeIn startFrame={10} durationFrames={15}>
          <div
            style={{
              ...card,
              borderRadius: '16px 16px 0 0',
              borderBottom: 'none',
              padding: '16px 24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', gap: 24 }}>
              {['All (3)', 'Pending (2)', 'Assigned (1)'].map((tab, i) => (
                <span
                  key={tab}
                  style={{
                    fontSize: 14,
                    fontWeight: i === 0 ? 700 : 400,
                    color: i === 0 ? COLORS.primary : COLORS.textDim,
                    borderBottom: i === 0 ? `2px solid ${COLORS.primary}` : 'none',
                    paddingBottom: 4,
                  }}
                >
                  {tab}
                </span>
              ))}
            </div>
            <div
              style={{
                fontSize: 13,
                color: COLORS.textDim,
                fontFamily: FONTS.mono,
              }}
            >
              Reviewer: Jane D.
            </div>
          </div>
        </FadeIn>

        {/* Queue items */}
        {REQUESTS.map((req, i) => (
          <FadeIn key={req.id} startFrame={20 + i * 12} durationFrames={15}>
            <div
              style={{
                ...card,
                borderRadius: i === REQUESTS.length - 1 ? '0 0 16px 16px' : 0,
                borderTop: `1px solid ${COLORS.gray700}`,
                padding: '18px 24px',
                display: 'flex',
                alignItems: 'center',
                gap: 20,
                backgroundColor: selectedIdx === i ? `${COLORS.primary}11` : COLORS.bgCard,
                borderColor: selectedIdx === i ? COLORS.primary : COLORS.gray700,
                transition: 'all 0.3s',
              }}
            >
              {/* Priority badge */}
              <div
                style={badge(PRIORITY_COLORS[req.priority].text, PRIORITY_COLORS[req.priority].bg)}
              >
                {req.priority}
              </div>

              {/* Request info */}
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 600,
                    color: COLORS.text,
                    marginBottom: 4,
                  }}
                >
                  {req.action}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: COLORS.textDim,
                    fontFamily: FONTS.mono,
                  }}
                >
                  {req.id} · {req.agent}
                </div>
              </div>

              {/* SLA */}
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: req.slaColor,
                }}
              >
                ⏱ {req.sla}
              </div>

              {/* Claim button */}
              {i === 0 && !approved && (
                <div
                  style={{
                    padding: '6px 16px',
                    borderRadius: 6,
                    backgroundColor: selectedIdx === 0 ? COLORS.primary : `${COLORS.primary}22`,
                    color: selectedIdx === 0 ? COLORS.white : COLORS.primaryLight,
                    fontSize: 13,
                    fontWeight: 600,
                    border: `1px solid ${COLORS.primary}44`,
                  }}
                >
                  {selectedIdx === 0 ? 'Claimed' : 'Claim'}
                </div>
              )}
            </div>
          </FadeIn>
        ))}
      </div>

      {/* Review panel (slides in when claimed) */}
      {selectedIdx === 0 && (
        <FadeIn startFrame={95} durationFrames={20}>
          <div
            style={{
              position: 'absolute',
              right: 80,
              top: 130,
              width: 480,
              ...card,
              padding: 0,
              overflow: 'hidden',
            }}
          >
            {/* Review header */}
            <div
              style={{
                padding: '16px 24px',
                borderBottom: `1px solid ${COLORS.gray700}`,
                backgroundColor: COLORS.bgCardLight,
              }}
            >
              <div style={{ fontSize: 16, fontWeight: 700 }}>Review: {REQUESTS[0].action}</div>
              <div
                style={{
                  fontSize: 13,
                  color: COLORS.textDim,
                  marginTop: 4,
                  fontFamily: FONTS.mono,
                }}
              >
                {REQUESTS[0].id} · {REQUESTS[0].agent}
              </div>
            </div>

            {/* Context */}
            <div style={{ padding: 24 }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: COLORS.textDim,
                  textTransform: 'uppercase',
                  letterSpacing: 1,
                  marginBottom: 8,
                }}
              >
                Agent Reasoning
              </div>
              <div
                style={{
                  fontSize: 14,
                  color: COLORS.textMuted,
                  lineHeight: 1.6,
                  marginBottom: 20,
                  padding: 14,
                  borderRadius: 8,
                  backgroundColor: `${COLORS.bgCard}`,
                  border: `1px solid ${COLORS.gray700}`,
                }}
              >
                Customer requested cancellation. Account has 12 days remaining on Pro plan ($49/mo).
                Prorated refund = $24.50. Policy allows immediate processing for accounts in good
                standing.
              </div>

              {/* Action buttons */}
              {showApprove && !approved && (
                <div style={{ display: 'flex', gap: 12 }}>
                  <div
                    style={{
                      flex: 1,
                      padding: '12px 0',
                      borderRadius: 8,
                      background: `linear-gradient(135deg, ${COLORS.green}, #16a34a)`,
                      textAlign: 'center',
                      fontSize: 14,
                      fontWeight: 700,
                      color: COLORS.white,
                      boxShadow: `0 4px 12px ${COLORS.green}44`,
                    }}
                  >
                    ✓ Approve
                  </div>
                  <div
                    style={{
                      flex: 1,
                      padding: '12px 0',
                      borderRadius: 8,
                      backgroundColor: COLORS.bgCardLight,
                      border: `1px solid ${COLORS.gray600}`,
                      textAlign: 'center',
                      fontSize: 14,
                      fontWeight: 600,
                      color: COLORS.textMuted,
                    }}
                  >
                    ✎ Edit
                  </div>
                  <div
                    style={{
                      padding: '12px 20px',
                      borderRadius: 8,
                      backgroundColor: `${COLORS.red}15`,
                      border: `1px solid ${COLORS.red}33`,
                      fontSize: 14,
                      fontWeight: 600,
                      color: COLORS.red,
                    }}
                  >
                    ✕
                  </div>
                </div>
              )}

              {/* Approved state */}
              {approved && (
                <FadeIn startFrame={160} durationFrames={10}>
                  <div
                    style={{
                      padding: '16px 0',
                      borderRadius: 8,
                      background: `linear-gradient(135deg, ${COLORS.green}22, ${COLORS.green}11)`,
                      border: `1px solid ${COLORS.green}44`,
                      textAlign: 'center',
                      fontSize: 16,
                      fontWeight: 700,
                      color: COLORS.green,
                    }}
                  >
                    ✓ Approved — Refund Processing
                  </div>
                </FadeIn>
              )}

              {/* Golden path saved indicator */}
              {showGoldenPath && (
                <FadeIn startFrame={185} durationFrames={15}>
                  <div
                    style={{
                      marginTop: 16,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '10px 16px',
                      borderRadius: 8,
                      backgroundColor: `${COLORS.accent}12`,
                      border: `1px solid ${COLORS.accent}33`,
                    }}
                  >
                    <span style={{ fontSize: 18 }}>🧠</span>
                    <div>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: COLORS.accentLight,
                        }}
                      >
                        Golden Path Saved
                      </div>
                      <div
                        style={{
                          fontSize: 12,
                          color: COLORS.textDim,
                        }}
                      >
                        This resolution will improve future responses
                      </div>
                    </div>
                  </div>
                </FadeIn>
              )}
            </div>
          </div>
        </FadeIn>
      )}
    </div>
  );
};
