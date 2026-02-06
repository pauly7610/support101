import type React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { FadeIn } from '../components/AnimatedText';
import { COLORS, FONTS, card, gradientBg, gridLines } from '../styles';

const GRAPH_NODES = [
  { id: 'customer', label: 'Customer', emoji: '👤', x: 200, y: 300, color: COLORS.primary },
  { id: 'ticket', label: 'Ticket', emoji: '🎫', x: 480, y: 180, color: COLORS.orange },
  { id: 'agent', label: 'Agent', emoji: '🤖', x: 760, y: 300, color: COLORS.accent },
  { id: 'resolution', label: 'Resolution', emoji: '✅', x: 1040, y: 180, color: COLORS.green },
  { id: 'article', label: 'Article', emoji: '📄', x: 1040, y: 420, color: COLORS.primaryLight },
  { id: 'playbook', label: 'Playbook', emoji: '📋', x: 1320, y: 300, color: COLORS.yellow },
];

const GRAPH_EDGES = [
  { from: 'customer', to: 'ticket', label: 'FILED' },
  { from: 'ticket', to: 'agent', label: 'ASSIGNED' },
  { from: 'agent', to: 'resolution', label: 'RESOLVED' },
  { from: 'resolution', to: 'article', label: 'USED' },
  { from: 'resolution', to: 'playbook', label: 'FOLLOWED' },
];

const STREAM_EVENTS = [
  { type: 'ticket.created', source: 'zendesk', time: '0.2s ago' },
  { type: 'agent.executed', source: 'internal', time: '0.8s ago' },
  { type: 'hitl.approved', source: 'internal', time: '1.2s ago' },
  { type: 'csat.received', source: 'webhook', time: '2.1s ago' },
  { type: 'playbook.suggested', source: 'engine', time: '2.3s ago' },
];

export const Scene6Learning: React.FC = () => {
  const frame = useCurrentFrame();

  const showFeedback = frame >= 0;
  const showStream = frame >= 90;
  const showGraph = frame >= 170;
  const showPlaybook = frame >= 260;
  const showCaption = frame >= 310;

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
            Continuous Learning System
          </span>
        </div>
      </FadeIn>

      {/* ── Phase 1: Feedback Loop ── */}
      {showFeedback && (
        <FadeIn startFrame={5} durationFrames={20}>
          <div
            style={{
              position: 'absolute',
              left: 80,
              top: 120,
              width: 420,
              ...card,
              padding: 0,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '14px 20px',
                borderBottom: `1px solid ${COLORS.gray700}`,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                backgroundColor: COLORS.bgCardLight,
              }}
            >
              <span style={{ fontSize: 20 }}>🧠</span>
              <span style={{ fontSize: 14, fontWeight: 700 }}>Feedback Loop</span>
              <span
                style={{
                  marginLeft: 'auto',
                  fontSize: 11,
                  fontFamily: FONTS.mono,
                  color: COLORS.green,
                }}
              >
                Pinecone
              </span>
            </div>

            {/* Golden path being written */}
            <div style={{ padding: 20 }}>
              <FadeIn startFrame={25} durationFrames={15}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: COLORS.textDim,
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                    marginBottom: 10,
                  }}
                >
                  Golden Path Captured
                </div>
              </FadeIn>

              <FadeIn startFrame={35} durationFrames={15}>
                <div
                  style={{
                    padding: 14,
                    borderRadius: 8,
                    backgroundColor: `${COLORS.green}10`,
                    border: `1px solid ${COLORS.green}33`,
                    fontSize: 13,
                    lineHeight: 1.6,
                  }}
                >
                  <div style={{ color: COLORS.green, fontWeight: 600, marginBottom: 6 }}>
                    ✓ Approved by Jane D.
                  </div>
                  <div style={{ color: COLORS.textMuted }}>
                    Query: "Cancel subscription + refund"
                  </div>
                  <div style={{ color: COLORS.textMuted }}>
                    Steps: analyze_intent → search_kb → calculate_refund
                  </div>
                  <div style={{ color: COLORS.textMuted }}>
                    Confidence: 94.2% · Category: billing
                  </div>
                </div>
              </FadeIn>

              {/* Vector upsert animation */}
              <FadeIn startFrame={55} durationFrames={15}>
                <div
                  style={{
                    marginTop: 12,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: 12,
                    fontFamily: FONTS.mono,
                    color: COLORS.primaryLight,
                  }}
                >
                  <div
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: COLORS.primaryLight,
                      boxShadow: `0 0 6px ${COLORS.primaryLight}`,
                    }}
                  />
                  Upserting to golden_paths namespace...
                </div>
              </FadeIn>

              <FadeIn startFrame={70} durationFrames={10}>
                <div
                  style={{
                    marginTop: 8,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: 12,
                    fontFamily: FONTS.mono,
                    color: COLORS.green,
                  }}
                >
                  <div
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: COLORS.green,
                      boxShadow: `0 0 6px ${COLORS.green}`,
                    }}
                  />
                  ✓ Vector stored (768 dims, cosine)
                </div>
              </FadeIn>
            </div>
          </div>
        </FadeIn>
      )}

      {/* ── Phase 2: Activity Stream ── */}
      {showStream && (
        <FadeIn startFrame={90} durationFrames={20}>
          <div
            style={{
              position: 'absolute',
              right: 80,
              top: 120,
              width: 420,
              ...card,
              padding: 0,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '14px 20px',
                borderBottom: `1px solid ${COLORS.gray700}`,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                backgroundColor: COLORS.bgCardLight,
              }}
            >
              <span style={{ fontSize: 20 }}>📡</span>
              <span style={{ fontSize: 14, fontWeight: 700 }}>Activity Stream</span>
              <span
                style={{
                  marginLeft: 'auto',
                  fontSize: 11,
                  fontFamily: FONTS.mono,
                  color: COLORS.red,
                }}
              >
                Redis Streams
              </span>
            </div>

            <div style={{ padding: '12px 20px' }}>
              {STREAM_EVENTS.map((evt, i) => (
                <FadeIn key={evt.type} startFrame={100 + i * 12} durationFrames={10}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '8px 0',
                      borderBottom:
                        i < STREAM_EVENTS.length - 1 ? `1px solid ${COLORS.gray700}44` : 'none',
                    }}
                  >
                    <div
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        backgroundColor:
                          evt.source === 'webhook'
                            ? COLORS.orange
                            : evt.source === 'engine'
                              ? COLORS.accent
                              : COLORS.primary,
                        boxShadow: `0 0 4px ${COLORS.primary}`,
                      }}
                    />
                    <span
                      style={{
                        fontSize: 13,
                        fontFamily: FONTS.mono,
                        color: COLORS.text,
                        flex: 1,
                      }}
                    >
                      {evt.type}
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        padding: '2px 8px',
                        borderRadius: 4,
                        backgroundColor: `${COLORS.gray700}`,
                        color: COLORS.textDim,
                      }}
                    >
                      {evt.source}
                    </span>
                    <span style={{ fontSize: 11, color: COLORS.textDim }}>{evt.time}</span>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </FadeIn>
      )}

      {/* ── Phase 3: Activity Graph ── */}
      {showGraph && (
        <FadeIn startFrame={170} durationFrames={20}>
          <div
            style={{
              position: 'absolute',
              left: 80,
              top: 520,
              right: 80,
              height: 340,
              ...card,
              padding: 0,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '14px 20px',
                borderBottom: `1px solid ${COLORS.gray700}`,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                backgroundColor: COLORS.bgCardLight,
              }}
            >
              <span style={{ fontSize: 20 }}>🕸️</span>
              <span style={{ fontSize: 14, fontWeight: 700 }}>Activity Graph</span>
              <span
                style={{
                  marginLeft: 'auto',
                  fontSize: 11,
                  fontFamily: FONTS.mono,
                  color: COLORS.primaryLight,
                }}
              >
                Apache AGE · Postgres
              </span>
            </div>

            {/* Graph visualization */}
            <div style={{ position: 'relative', height: 280, padding: 20 }}>
              {/* Edges */}
              <svg
                style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
                viewBox="0 0 1760 280"
                aria-label="Activity graph"
              >
                <title>Activity Graph</title>
                {GRAPH_EDGES.map((edge, i) => {
                  const from = GRAPH_NODES.find((n) => n.id === edge.from) ?? GRAPH_NODES[0];
                  const to = GRAPH_NODES.find((n) => n.id === edge.to) ?? GRAPH_NODES[0];
                  const edgeFrame = 185 + i * 15;
                  const progress = interpolate(frame, [edgeFrame, edgeFrame + 15], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  });
                  return (
                    <g key={`${edge.from}-${edge.to}`}>
                      <line
                        x1={from.x}
                        y1={from.y - 180}
                        x2={from.x + (to.x - from.x) * progress}
                        y2={from.y - 180 + (to.y - from.y) * progress}
                        stroke={COLORS.gray600}
                        strokeWidth={2}
                        strokeDasharray="6 4"
                        opacity={0.6}
                      />
                      {progress > 0.5 && (
                        <text
                          x={(from.x + to.x) / 2}
                          y={(from.y + to.y) / 2 - 185}
                          fill={COLORS.textDim}
                          fontSize={10}
                          fontFamily={FONTS.mono}
                          textAnchor="middle"
                          opacity={interpolate(progress, [0.5, 1], [0, 1])}
                        >
                          {edge.label}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>

              {/* Nodes */}
              {GRAPH_NODES.map((node, i) => {
                const nodeFrame = 180 + i * 10;
                const nodeProgress = interpolate(frame, [nodeFrame, nodeFrame + 12], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                });
                const scale = interpolate(nodeProgress, [0, 1], [0.5, 1]);
                return (
                  <div
                    key={node.id}
                    style={{
                      position: 'absolute',
                      left: node.x - 40,
                      top: node.y - 210,
                      width: 80,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 6,
                      opacity: nodeProgress,
                      transform: `scale(${scale})`,
                    }}
                  >
                    <div
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: '50%',
                        backgroundColor: `${node.color}22`,
                        border: `2px solid ${node.color}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 22,
                        boxShadow: `0 0 16px ${node.color}33`,
                      }}
                    >
                      {node.emoji}
                    </div>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: COLORS.textMuted,
                        fontFamily: FONTS.mono,
                      }}
                    >
                      {node.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </FadeIn>
      )}

      {/* ── Phase 4: Playbook suggestion ── */}
      {showPlaybook && (
        <FadeIn startFrame={260} durationFrames={20}>
          <div
            style={{
              position: 'absolute',
              left: 560,
              top: 120,
              width: 420,
              ...card,
              padding: 20,
              borderColor: COLORS.yellow,
              boxShadow: `0 0 24px ${COLORS.yellow}15, 0 8px 32px rgba(0,0,0,0.3)`,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                marginBottom: 14,
              }}
            >
              <span style={{ fontSize: 22 }}>📋</span>
              <span style={{ fontSize: 15, fontWeight: 700 }}>Playbook Suggested</span>
              <span
                style={{
                  marginLeft: 'auto',
                  fontSize: 11,
                  fontFamily: FONTS.mono,
                  color: COLORS.accent,
                }}
              >
                LangGraph
              </span>
            </div>

            <div
              style={{
                padding: 14,
                borderRadius: 8,
                backgroundColor: `${COLORS.yellow}10`,
                border: `1px solid ${COLORS.yellow}33`,
                marginBottom: 12,
              }}
            >
              <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.yellow, marginBottom: 6 }}>
                Billing Resolution (SupportAgent)
              </div>
              <div style={{ fontSize: 13, color: COLORS.textMuted, lineHeight: 1.5 }}>
                Auto-generated from 12 successful traces
              </div>
            </div>

            {/* Steps */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {['analyze_intent', 'search_kb', 'calculate_refund', 'confirm_action'].map(
                (step, i) => (
                  <FadeIn key={step} startFrame={275 + i * 8} durationFrames={10}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        fontSize: 13,
                      }}
                    >
                      <div
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: '50%',
                          backgroundColor: `${COLORS.accent}22`,
                          border: `1px solid ${COLORS.accent}44`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 11,
                          fontWeight: 700,
                          color: COLORS.accentLight,
                        }}
                      >
                        {i + 1}
                      </div>
                      <span style={{ fontFamily: FONTS.mono, color: COLORS.text }}>{step}</span>
                      {i < 3 && <span style={{ color: COLORS.textDim, fontSize: 16 }}>→</span>}
                    </div>
                  </FadeIn>
                ),
              )}
            </div>

            {/* Success rate */}
            <FadeIn startFrame={305} durationFrames={10}>
              <div
                style={{
                  marginTop: 14,
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 13,
                }}
              >
                <span style={{ color: COLORS.green, fontWeight: 700 }}>92% success rate</span>
                <span style={{ color: COLORS.textDim }}>12 samples</span>
              </div>
            </FadeIn>
          </div>
        </FadeIn>
      )}

      {/* Bottom caption */}
      {showCaption && (
        <FadeIn startFrame={310} durationFrames={20}>
          <div
            style={{
              position: 'absolute',
              bottom: 60,
              left: 0,
              right: 0,
              textAlign: 'center',
            }}
          >
            <div
              style={{
                fontSize: 24,
                fontWeight: 700,
                fontFamily: FONTS.heading,
                color: COLORS.text,
              }}
            >
              Every interaction teaches the system.{' '}
              <span style={{ color: COLORS.primaryLight }}>No fine-tuning required.</span>
            </div>
          </div>
        </FadeIn>
      )}
    </div>
  );
};
