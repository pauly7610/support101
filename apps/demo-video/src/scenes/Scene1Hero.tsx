import type React from 'react';
import { Easing, interpolate, useCurrentFrame } from 'remotion';
import { AnimatedText, FadeIn } from '../components/AnimatedText';
import { COLORS, FONTS, bodyText, gradientBg, gridLines, heading1 } from '../styles';

export const Scene1Hero: React.FC = () => {
  const frame = useCurrentFrame();

  const logoScale = interpolate(frame, [0, 25], [0.5, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.back(1.4)),
  });
  const logoOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const orbitAngle = interpolate(frame, [0, 300], [0, 360]);

  return (
    <div style={gradientBg}>
      <div style={gridLines} />

      {/* Orbiting dots */}
      {[0, 120, 240].map((offset, i) => {
        const angle = ((orbitAngle + offset) * Math.PI) / 180;
        const radius = 320;
        const colors = [COLORS.primary, COLORS.accent, COLORS.green];
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: 960 + Math.cos(angle) * radius - 8,
              top: 540 + Math.sin(angle) * radius - 8,
              width: 16,
              height: 16,
              borderRadius: '50%',
              backgroundColor: colors[i],
              boxShadow: `0 0 20px ${colors[i]}, 0 0 40px ${colors[i]}44`,
              opacity: interpolate(frame, [10, 30], [0, 0.7], {
                extrapolateRight: 'clamp',
              }),
            }}
          />
        );
      })}

      {/* Brain icon / logo */}
      <div
        style={{
          opacity: logoOpacity,
          transform: `scale(${logoScale})`,
          fontSize: 80,
          marginBottom: 32,
        }}
      >
        🧠
      </div>

      {/* Title */}
      <AnimatedText
        text="Support Intelligence Core"
        startFrame={15}
        durationFrames={25}
        style={{
          ...heading1,
          background: `linear-gradient(135deg, ${COLORS.white} 0%, ${COLORS.primaryLight} 50%, ${COLORS.accentLight} 100%)`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          textAlign: 'center',
        }}
      />

      {/* Subtitle */}
      <FadeIn startFrame={45} durationFrames={20}>
        <div
          style={{
            ...bodyText,
            fontSize: 28,
            textAlign: 'center',
            maxWidth: 800,
            marginTop: 24,
          }}
        >
          What if your support agents got smarter with every ticket?
        </div>
      </FadeIn>

      {/* Tech pills */}
      <FadeIn startFrame={75} durationFrames={20}>
        <div style={{ display: 'flex', gap: 16, marginTop: 40 }}>
          {['LangChain', 'Pinecone', 'Redis Streams', 'Apache AGE', 'LangGraph'].map((tech, i) => (
            <div
              key={tech}
              style={{
                padding: '8px 20px',
                borderRadius: 9999,
                border: `1px solid ${COLORS.gray600}`,
                backgroundColor: `${COLORS.gray800}cc`,
                fontSize: 15,
                fontFamily: FONTS.mono,
                color: COLORS.primaryLight,
                opacity: interpolate(frame, [75 + i * 5, 85 + i * 5], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                }),
                transform: `translateY(${interpolate(frame, [75 + i * 5, 85 + i * 5], [10, 0], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                })}px)`,
              }}
            >
              {tech}
            </div>
          ))}
        </div>
      </FadeIn>
    </div>
  );
};
