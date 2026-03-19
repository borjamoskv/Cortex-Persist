import React from 'react';
import {
  AbsoluteFill,
  Sequence,
  Img,
  useCurrentFrame,
  interpolate,
  staticFile,
  random,
} from 'remotion';
import {HERNARO_SCENES, type HernароScene} from './hernaro-scenes';
import {SceneTransition} from './components/SceneTransition';
import {ParticleField} from './components/ParticleField';
import {CameraShake} from './components/CameraShake';
import {DataRain} from './components/DataRain';
import {NeuralGrid} from './components/NeuralGrid';
import {VoidFade} from './components/VoidFade';

/* ═══════════════════════════════════════════════════════════════
   TYPOGRAPHIC SCENE — Each Naroa gets a cinematic title card
   ═══════════════════════════════════════════════════════════════ */

const HernароTitle: React.FC<{scene: HernароScene}> = ({scene}) => {
  const frame = useCurrentFrame();

  // Entrance: stagger lines
  const titleOpacity = interpolate(frame, [0, 25], [0, 1], {extrapolateRight: 'clamp'});
  const titleY = interpolate(frame, [0, 25], [40, 0], {extrapolateRight: 'clamp'});
  const subtitleOpacity = interpolate(frame, [15, 40], [0, 1], {extrapolateRight: 'clamp'});
  const subtitleY = interpolate(frame, [15, 40], [30, 0], {extrapolateRight: 'clamp'});
  const textOpacity = interpolate(frame, [30, 55], [0, 1], {extrapolateRight: 'clamp'});
  const textY = interpolate(frame, [30, 55], [20, 0], {extrapolateRight: 'clamp'});

  // Gold shimmer for title
  const shimmer = Math.sin(frame * 0.1) * 10 + 10;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10,
        padding: '0 10%',
      }}
    >
      {/* Roman numeral / Title */}
      <div
        style={{
          fontFamily: "'Georgia', 'Times New Roman', serif",
          fontSize: scene.id === 'intro' ? 110 : scene.id === 'epilogo' ? 72 : 48,
          fontWeight: 700,
          color: scene.colorAccent,
          textTransform: 'uppercase',
          letterSpacing: scene.id === 'intro' ? '0.15em' : '0.08em',
          textAlign: 'center',
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          textShadow: `0 0 ${shimmer}px ${scene.colorAccent}80, 0 0 ${shimmer * 2}px ${scene.colorAccent}40`,
        }}
      >
        {scene.title}
      </div>

      {/* Subtitle / Material */}
      <div
        style={{
          fontFamily: "'Georgia', serif",
          fontSize: 22,
          fontWeight: 400,
          fontStyle: 'italic',
          color: '#FFFFFF90',
          marginTop: 16,
          letterSpacing: '0.12em',
          textAlign: 'center',
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
        }}
      >
        {scene.subtitle}
      </div>

      {/* Divider line */}
      <div
        style={{
          width: interpolate(frame, [20, 50], [0, 200], {extrapolateRight: 'clamp'}),
          height: 1,
          backgroundColor: scene.colorAccent,
          marginTop: 24,
          marginBottom: 24,
          opacity: 0.6,
          boxShadow: `0 0 10px ${scene.colorAccent}60`,
        }}
      />

      {/* Body text */}
      <div
        style={{
          fontFamily: "'Georgia', serif",
          fontSize: scene.id === 'epilogo' ? 36 : 28,
          fontWeight: 300,
          color: '#FFFFFFD0',
          textAlign: 'center',
          lineHeight: 1.6,
          maxWidth: '70%',
          whiteSpace: 'pre-line',
          opacity: textOpacity,
          transform: `translateY(${textY}px)`,
        }}
      >
        {scene.text}
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   ARTWORK LAYER — Slow ken-burns on the artwork
   ═══════════════════════════════════════════════════════════════ */

const ArtworkLayer: React.FC<{artwork: string; colorAccent: string}> = ({
  artwork,
  colorAccent,
}) => {
  const frame = useCurrentFrame();

  const scale = interpolate(frame, [0, 150], [1.05, 1.15], {extrapolateRight: 'clamp'});
  const opacity = interpolate(frame, [0, 30, 120, 150], [0, 0.4, 0.4, 0], {
    extrapolateRight: 'clamp',
  });
  const x = Math.sin(frame * 0.02) * 20;
  const y = Math.cos(frame * 0.015) * 15;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        zIndex: 2,
      }}
    >
      <Img
        src={staticFile(artwork)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale}) translate(${x}px, ${y}px)`,
          opacity,
          filter: `grayscale(0.6) contrast(1.2) brightness(0.7)`,
        }}
      />
      {/* Color tint overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: colorAccent,
          opacity: 0.08,
          mixBlendMode: 'overlay',
        }}
      />
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   SCENE BACKGROUNDS — Effect per Naroa type
   ═══════════════════════════════════════════════════════════════ */

const HernароBackground: React.FC<{scene: HernароScene}> = ({scene}) => {
  const frame = useCurrentFrame();

  switch (scene.effect) {
    case 'void':
      return <VoidFade fadeIn />;

    case 'mineral': {
      // Fractured stone texture — diagonal lines
      const lines = Array.from({length: 20}, (_, i) => ({
        angle: random(`ml-a-${i}`) * 180,
        x: random(`ml-x-${i}`) * 100,
        y: random(`ml-y-${i}`) * 100,
        len: 50 + random(`ml-l-${i}`) * 200,
        opacity: 0.03 + random(`ml-o-${i}`) * 0.05,
      }));
      return (
        <div style={{...fullBlack}}>
          {lines.map((l, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${l.x}%`,
                top: `${l.y}%`,
                width: l.len,
                height: 1,
                backgroundColor: scene.colorAccent,
                opacity: l.opacity,
                transform: `rotate(${l.angle}deg)`,
              }}
            />
          ))}
        </div>
      );
    }

    case 'glow': {
      // Shimmering mica particles
      const particles = Array.from({length: 40}, (_, i) => ({
        x: random(`gp-x-${i}`) * 100,
        y: random(`gp-y-${i}`) * 100,
        size: 1 + random(`gp-s-${i}`) * 4,
        twinkle: Math.sin(frame * 0.1 + random(`gp-t-${i}`) * 10) * 0.5 + 0.5,
      }));
      return (
        <div style={{...fullBlack, background: 'radial-gradient(ellipse at 50% 40%, #1a1a2e 0%, #0A0A0A 70%)'}}>
          {particles.map((p, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${p.x}%`,
                top: `${p.y}%`,
                width: p.size,
                height: p.size,
                borderRadius: '50%',
                backgroundColor: '#E2E8F0',
                opacity: p.twinkle * 0.6,
                boxShadow: `0 0 ${p.size * 3}px #E2E8F0`,
              }}
            />
          ))}
        </div>
      );
    }

    case 'kintsugi': {
      // Gold cracks on black
      const cracks = Array.from({length: 8}, (_, i) => {
        const startX = random(`kc-sx-${i}`) * 100;
        const startY = random(`kc-sy-${i}`) * 100;
        const angle = random(`kc-a-${i}`) * 360;
        const len = 100 + random(`kc-l-${i}`) * 300;
        const grow = interpolate(frame, [10 + i * 8, 30 + i * 8], [0, 1], {extrapolateRight: 'clamp'});
        return {startX, startY, angle, len: len * grow};
      });
      return (
        <div style={{...fullBlack}}>
          {cracks.map((c, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${c.startX}%`,
                top: `${c.startY}%`,
                width: c.len,
                height: 2,
                backgroundColor: '#d4af37',
                opacity: 0.7,
                transform: `rotate(${c.angle}deg)`,
                transformOrigin: '0 50%',
                boxShadow: '0 0 8px #d4af3780, 0 0 20px #d4af3740',
              }}
            />
          ))}
        </div>
      );
    }

    case 'gold': {
      const pulse = Math.sin(frame * 0.08) * 0.3 + 0.7;
      return (
        <div
          style={{
            ...fullBlack,
            background: `radial-gradient(ellipse at 50% 50%, #d4af3720 0%, #0A0A0A 60%)`,
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              width: 400,
              height: 400,
              transform: 'translate(-50%, -50%)',
              borderRadius: '50%',
              border: '1px solid #d4af3740',
              opacity: pulse,
              boxShadow: `0 0 60px #d4af3720, inset 0 0 40px #d4af3710`,
            }}
          />
        </div>
      );
    }

    case 'digital':
      return (
        <>
          <div style={{...fullBlack}} />
          <DataRain color="#2B3BE5" columns={40} speed={1.5} />
          <NeuralGrid color="#2B3BE5" nodeCount={30} />
        </>
      );

    case 'typewriter': {
      // Pulsing cursor for the AI epilogue
      const cursorVisible = frame % 30 < 15;
      return (
        <div style={{...fullBlack, background: 'radial-gradient(ellipse at 50% 50%, #0f0f2a 0%, #0A0A0A 70%)'}}>
          {cursorVisible && (
            <div
              style={{
                position: 'absolute',
                bottom: 100,
                left: '50%',
                width: 2,
                height: 24,
                backgroundColor: '#2B3BE5',
                boxShadow: '0 0 10px #2B3BE5',
              }}
            />
          )}
        </div>
      );
    }

    default:
      return <div style={{...fullBlack}} />;
  }
};

/* ═══════════════════════════════════════════════════════════════
   JULIO CORTEZA WATERMARK
   ═══════════════════════════════════════════════════════════════ */

const JulioCortezaWatermark: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [60, 90], [0, 0.15], {extrapolateRight: 'clamp'});

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 30,
        left: 40,
        fontFamily: "'Courier New', monospace",
        fontSize: 13,
        color: '#FFFFFF',
        opacity,
        letterSpacing: '0.1em',
        zIndex: 30,
      }}
    >
      JULIO CORTEZA · IA · naroa.online
    </div>
  );
};

/* Scene counter */
const SceneCounter: React.FC<{current: number; total: number; color: string}> = ({
  current,
  total,
  color,
}) => (
  <div
    style={{
      position: 'absolute',
      top: 30,
      right: 40,
      fontFamily: "'Courier New', monospace",
      fontSize: 14,
      color,
      opacity: 0.4,
      letterSpacing: '0.15em',
      zIndex: 30,
    }}
  >
    {String(current).padStart(2, '0')} / {total}
  </div>
);

/* ═══════════════════════════════════════════════════════════════
   MAIN COMPOSITION
   ═══════════════════════════════════════════════════════════════ */

export const ElGranHernaro: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0A0A0A'}}>
      {/* Global atmospheric particles */}
      <CameraShake intensity={0.3}>
        <ParticleField color="#d4af37" count={20} />

        {/* Scenes */}
        {HERNARO_SCENES.map((scene, index) => (
          <Sequence
            key={scene.id}
            from={scene.startFrame}
            durationInFrames={scene.durationFrames}
            name={scene.id}
          >
            <SceneTransition direction="in" duration={20}>
              <AbsoluteFill>
                {/* Background effect */}
                <HernароBackground scene={scene} />

                {/* Artwork layer (if present) */}
                {scene.artwork && (
                  <ArtworkLayer
                    artwork={scene.artwork}
                    colorAccent={scene.colorAccent}
                  />
                )}

                {/* Scene-specific particles */}
                <ParticleField color={scene.colorAccent} count={15} />

                {/* Title card */}
                <HernароTitle scene={scene} />

                {/* Scene counter */}
                {scene.id !== 'intro' && scene.id !== 'epilogo' && (
                  <SceneCounter
                    current={index}
                    total={12}
                    color={scene.colorAccent}
                  />
                )}
              </AbsoluteFill>
            </SceneTransition>
          </Sequence>
        ))}
      </CameraShake>

      {/* Persistent HUD */}
      <JulioCortezaWatermark />

      {/* Top-left brand */}
      <div
        style={{
          position: 'absolute',
          top: 30,
          left: 40,
          fontFamily: "'Georgia', serif",
          fontSize: 12,
          fontWeight: 400,
          color: '#FFFFFF10',
          letterSpacing: '0.25em',
          textTransform: 'uppercase',
          zIndex: 30,
        }}
      >
        EL GRAN HERNARO
      </div>
    </AbsoluteFill>
  );
};

const fullBlack: React.CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  backgroundColor: '#0A0A0A',
};
