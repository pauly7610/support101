import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

interface AnimatedTextProps {
  text: string;
  startFrame?: number;
  durationFrames?: number;
  style?: React.CSSProperties;
  direction?: "up" | "down" | "left" | "right";
}

export const AnimatedText: React.FC<AnimatedTextProps> = ({
  text,
  startFrame = 0,
  durationFrames = 20,
  style = {},
  direction = "up",
}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(
    frame,
    [startFrame, startFrame + durationFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const translateMap = {
    up: `translateY(${interpolate(progress, [0, 1], [40, 0])}px)`,
    down: `translateY(${interpolate(progress, [0, 1], [-40, 0])}px)`,
    left: `translateX(${interpolate(progress, [0, 1], [40, 0])}px)`,
    right: `translateX(${interpolate(progress, [0, 1], [-40, 0])}px)`,
  };

  return (
    <div
      style={{
        opacity: progress,
        transform: translateMap[direction],
        ...style,
      }}
    >
      {text}
    </div>
  );
};

interface TypewriterProps {
  text: string;
  startFrame?: number;
  charsPerFrame?: number;
  style?: React.CSSProperties;
  cursorColor?: string;
}

export const Typewriter: React.FC<TypewriterProps> = ({
  text,
  startFrame = 0,
  charsPerFrame = 0.8,
  style = {},
  cursorColor = "#3b82f6",
}) => {
  const frame = useCurrentFrame();
  const elapsed = Math.max(0, frame - startFrame);
  const chars = Math.min(Math.floor(elapsed * charsPerFrame), text.length);
  const showCursor = elapsed > 0 && chars < text.length;

  return (
    <span style={style}>
      {text.slice(0, chars)}
      {showCursor && (
        <span
          style={{
            borderRight: `2px solid ${cursorColor}`,
            marginLeft: 1,
            animation: "blink 0.8s step-end infinite",
          }}
        />
      )}
    </span>
  );
};

interface FadeInProps {
  children: React.ReactNode;
  startFrame?: number;
  durationFrames?: number;
  style?: React.CSSProperties;
}

export const FadeIn: React.FC<FadeInProps> = ({
  children,
  startFrame = 0,
  durationFrames = 15,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [startFrame, startFrame + durationFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const y = interpolate(
    frame,
    [startFrame, startFrame + durationFrames],
    [20, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div style={{ opacity, transform: `translateY(${y}px)`, ...style }}>
      {children}
    </div>
  );
};

interface ScaleInProps {
  children: React.ReactNode;
  startFrame?: number;
  durationFrames?: number;
  style?: React.CSSProperties;
}

export const ScaleIn: React.FC<ScaleInProps> = ({
  children,
  startFrame = 0,
  durationFrames = 15,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(
    frame,
    [startFrame, startFrame + durationFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const scale = interpolate(progress, [0, 1], [0.8, 1]);

  return (
    <div
      style={{
        opacity: progress,
        transform: `scale(${scale})`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
