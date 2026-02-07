import type React from 'react';
import { useCurrentFrame } from 'remotion';
import { FadeIn, ScaleIn } from '../components/AnimatedText';
import { COLORS, FONTS, card, gradientBg, gridLines } from '../styles';

const METRICS = [
  { label: 'Total Agents', value: '24', sub: '9 active', color: COLORS.text },
  { label: 'Awaiting Human', value: '3', sub: '', color: COLORS.yellow },
  { label: 'HITL Pending', value: '7', sub: '42 completed', color: COLORS.primary },
  { label: 'Audit Events', value: '1,847', sub: '128 recent', color: COLORS.text },
];

const AGENTS = [
  { name: 'Support Bot Alpha', blueprint: 'support_agent', status: 'running', tenant: 'acme-corp' },
  { name: 'Triage Router', blueprint: 'triage_agent', status: 'running', tenant: 'acme-corp' },
  {
    name: 'Billing Assistant',
    blueprint: 'support_agent',
    status: 'awaiting_human',
    tenant: 'globex',
  },
  {
    name: 'Compliance Scanner',
    blueprint: 'compliance_auditor',
    status: 'running',
    tenant: 'initech',
  },
  { name: 'Onboarding Guide', blueprint: 'onboarding_agent', status: 'idle', tenant: 'globex' },
];

const AUDIT_EVENTS = [
  { type: 'execution_completed', agent: 'Support Bot Alpha', time: '2s ago', color: COLORS.green },
  {
    type: 'human_feedback_provided',
    agent: 'Billing Assistant',
    time: '14s ago',
    color: COLORS.accent,
  },
  { type: 'execution_started', agent: 'Triage Router', time: '31s ago', color: COLORS.primary },
  { type: 'agent_created', agent: 'Sentiment Monitor', time: '2m ago', color: COLORS.primaryLight },
];

const STATUS_COLORS: Record<string, string> = {
  running: COLORS.green,
  idle: COLORS.gray500,
  awaiting_human: COLORS.yellow,
  failed: COLORS.red,
};

export const Scene5Governance: React.FC = () => {
  const frame = useCurrentFrame();
  const showAgents = frame >= 90;
  const showAudit = frame >= 160;

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
              backgroundColor: COLORS.primary,
              boxShadow: `0 0 8px ${COLORS.primary}`,
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
            Governance Dashboard
          </span>
        </div>
      </FadeIn>

      {/* Metric cards */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 80,
          right: 80,
          display: 'flex',
          gap: 20,
        }}
      >
        {METRICS.map((m, i) => (
          <ScaleIn key={m.label} startFrame={10 + i * 8} durationFrames={15}>
            <div
              style={{
                ...card,
                flex: 1,
                padding: '20px 24px',
              }}
            >
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
                {m.label}
              </div>
              <div
                style={{
                  fontSize: 36,
                  fontWeight: 800,
                  color: m.color,
                  fontFamily: FONTS.heading,
                }}
              >
                {m.value}
              </div>
              {m.sub && (
                <div style={{ fontSize: 13, color: COLORS.textDim, marginTop: 4 }}>{m.sub}</div>
              )}
            </div>
          </ScaleIn>
        ))}
      </div>

      {/* SLA compliance bar */}
      <FadeIn startFrame={55} durationFrames={15}>
        <div
          style={{
            position: 'absolute',
            top: 280,
            left: 80,
            right: 80,
            ...card,
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.textDim, marginBottom: 4 }}>
              SLA Compliance
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  backgroundColor: COLORS.green,
                  boxShadow: `0 0 6px ${COLORS.green}`,
                }}
              />
              <span style={{ fontSize: 15, fontWeight: 700, color: COLORS.green }}>
                97.3% — All SLAs Met
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 24, fontSize: 14 }}>
            <span>
              <span style={{ fontWeight: 700, color: COLORS.green }}>42</span>{' '}
              <span style={{ color: COLORS.textDim }}>resolved</span>
            </span>
            <span>
              <span style={{ fontWeight: 700, color: COLORS.red }}>1</span>{' '}
              <span style={{ color: COLORS.textDim }}>expired</span>
            </span>
          </div>
        </div>
      </FadeIn>

      {/* Agents table */}
      {showAgents && (
        <FadeIn startFrame={90} durationFrames={20}>
          <div
            style={{
              position: 'absolute',
              top: 380,
              left: 80,
              right: 80,
              ...card,
              padding: 0,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '14px 24px',
                borderBottom: `1px solid ${COLORS.gray700}`,
                fontSize: 14,
                fontWeight: 700,
                color: COLORS.text,
                backgroundColor: COLORS.bgCardLight,
              }}
            >
              Active Agents
            </div>
            {/* Header row */}
            <div
              style={{
                display: 'flex',
                padding: '10px 24px',
                borderBottom: `1px solid ${COLORS.gray700}`,
                fontSize: 11,
                fontWeight: 600,
                color: COLORS.textDim,
                textTransform: 'uppercase',
                letterSpacing: 1,
              }}
            >
              <div style={{ flex: 2 }}>Agent</div>
              <div style={{ flex: 1.5 }}>Blueprint</div>
              <div style={{ flex: 1 }}>Status</div>
              <div style={{ flex: 1 }}>Tenant</div>
            </div>
            {/* Rows */}
            {AGENTS.map((agent, i) => (
              <FadeIn key={agent.name} startFrame={100 + i * 8} durationFrames={12}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '12px 24px',
                    borderBottom: i < AGENTS.length - 1 ? `1px solid ${COLORS.gray700}44` : 'none',
                    fontSize: 14,
                  }}
                >
                  <div style={{ flex: 2 }}>
                    <div style={{ fontWeight: 600, color: COLORS.text }}>{agent.name}</div>
                  </div>
                  <div style={{ flex: 1.5 }}>
                    <span
                      style={{
                        padding: '3px 10px',
                        borderRadius: 4,
                        backgroundColor: `${COLORS.gray700}`,
                        fontSize: 12,
                        color: COLORS.textMuted,
                        fontFamily: FONTS.mono,
                      }}
                    >
                      {agent.blueprint}
                    </span>
                  </div>
                  <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: STATUS_COLORS[agent.status] || COLORS.gray500,
                        boxShadow: `0 0 4px ${STATUS_COLORS[agent.status] || COLORS.gray500}`,
                      }}
                    />
                    <span style={{ color: COLORS.textMuted, fontSize: 13 }}>
                      {agent.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div
                    style={{
                      flex: 1,
                      fontSize: 13,
                      color: COLORS.textDim,
                      fontFamily: FONTS.mono,
                    }}
                  >
                    {agent.tenant}
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </FadeIn>
      )}

      {/* Audit log */}
      {showAudit && (
        <FadeIn startFrame={160} durationFrames={20}>
          <div
            style={{
              position: 'absolute',
              top: 700,
              left: 80,
              right: 80,
              ...card,
              padding: 0,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '14px 24px',
                borderBottom: `1px solid ${COLORS.gray700}`,
                fontSize: 14,
                fontWeight: 700,
                color: COLORS.text,
                backgroundColor: COLORS.bgCardLight,
              }}
            >
              Audit Log
            </div>
            {AUDIT_EVENTS.map((evt, i) => (
              <FadeIn key={evt.type} startFrame={170 + i * 10} durationFrames={12}>
                <div
                  style={{
                    padding: '12px 24px',
                    borderBottom:
                      i < AUDIT_EVENTS.length - 1 ? `1px solid ${COLORS.gray700}44` : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                  }}
                >
                  <div
                    style={{
                      padding: '3px 10px',
                      borderRadius: 9999,
                      backgroundColor: `${evt.color}22`,
                      fontSize: 11,
                      fontWeight: 600,
                      color: evt.color,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {evt.type.replace(/_/g, ' ')}
                  </div>
                  <div style={{ flex: 1, fontSize: 13, color: COLORS.textMuted }}>{evt.agent}</div>
                  <div style={{ fontSize: 12, color: COLORS.textDim }}>{evt.time}</div>
                </div>
              </FadeIn>
            ))}
          </div>
        </FadeIn>
      )}
    </div>
  );
};
