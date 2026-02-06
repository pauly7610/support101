import React from "react";
import { Composition, Series } from "remotion";
import { Scene1Hero } from "./scenes/Scene1Hero";
import { Scene2ChatWidget } from "./scenes/Scene2ChatWidget";
import { Scene3Copilot } from "./scenes/Scene3Copilot";
import { Scene4HITL } from "./scenes/Scene4HITL";
import { Scene5Governance } from "./scenes/Scene5Governance";
import { Scene6Learning } from "./scenes/Scene6Learning";
import { Scene7Closing } from "./scenes/Scene7Closing";

// 30fps, 1080p
const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

// Scene durations in frames (at 30fps)
const SCENE_DURATIONS = {
  hero: 4 * FPS,        // 4s
  chat: 8 * FPS,        // 8s
  copilot: 9 * FPS,     // 9s
  hitl: 7 * FPS,        // 7s
  governance: 7 * FPS,  // 7s
  learning: 12 * FPS,   // 12s
  closing: 6 * FPS,     // 6s
};

const TOTAL_DURATION = Object.values(SCENE_DURATIONS).reduce((a, b) => a + b, 0);

/**
 * Full demo video — all 7 scenes stitched together using Remotion Series.
 * Total: ~53 seconds at 30fps.
 */
const DemoVideoComposition: React.FC = () => {
  return (
    <Series>
      <Series.Sequence durationInFrames={SCENE_DURATIONS.hero}>
        <Scene1Hero />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENE_DURATIONS.chat}>
        <Scene2ChatWidget />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENE_DURATIONS.copilot}>
        <Scene3Copilot />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENE_DURATIONS.hitl}>
        <Scene4HITL />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENE_DURATIONS.governance}>
        <Scene5Governance />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENE_DURATIONS.learning}>
        <Scene6Learning />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENE_DURATIONS.closing}>
        <Scene7Closing />
      </Series.Sequence>
    </Series>
  );
};

/**
 * Remotion Root — registers the main composition and individual scene previews.
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Full video */}
      <Composition
        id="DemoVideo"
        component={DemoVideoComposition}
        durationInFrames={TOTAL_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />

      {/* Individual scene previews for development */}
      <Composition
        id="Scene1-Hero"
        component={Scene1Hero}
        durationInFrames={SCENE_DURATIONS.hero}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Scene2-ChatWidget"
        component={Scene2ChatWidget}
        durationInFrames={SCENE_DURATIONS.chat}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Scene3-Copilot"
        component={Scene3Copilot}
        durationInFrames={SCENE_DURATIONS.copilot}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Scene4-HITL"
        component={Scene4HITL}
        durationInFrames={SCENE_DURATIONS.hitl}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Scene5-Governance"
        component={Scene5Governance}
        durationInFrames={SCENE_DURATIONS.governance}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Scene6-Learning"
        component={Scene6Learning}
        durationInFrames={SCENE_DURATIONS.learning}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Scene7-Closing"
        component={Scene7Closing}
        durationInFrames={SCENE_DURATIONS.closing}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  );
};
