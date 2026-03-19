import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  useCurrentFrame,
  staticFile,
  random,
  interpolate,
} from 'remotion';
import {SCENES, BEAT_FRAMES, BAR_FRAMES, type LyricScene} from './lyrics';
import {BeatReactor, useBeat} from './components/BeatReactor';
import {CameraShake} from './components/CameraShake';
import {ParticleField} from './components/ParticleField';
import {SceneTransition} from './components/SceneTransition';
import {ArtworkFlash} from './components/ArtworkFlash';
import {GlitchText} from './components/GlitchText';
import {DataRain} from './components/DataRain';
import {CRTEffect} from './components/CRTEffect';
import {NeuralGrid} from './components/NeuralGrid';
import {BIOSBoot} from './components/BIOSBoot';
import {StrobeFlash} from './components/StrobeFlash';
import {VoidFade} from './components/VoidFade';

/** Background per effect type */
const SceneBackground: React.FC<{scene: LyricScene}> = ({scene}) => {
  const frame = useCurrentFrame();

  switch (scene.effect) {
    case 'rain':
      return (
        <>
          <div style={{...fullBlack}} />
          <DataRain color={scene.colorAccent} columns={55} speed={2.5} />
        </>
      );

    case 'crt':
      return (
        <>
          <div
            style={{
              ...fullBlack,
              background: `radial-gradient(ellipse at center, ${scene.colorAccent}15 0%, #0A0A0A 70%)`,
            }}
          />
          <CRTEffect
            colorTint={scene.colorAccent}
            powerOff={scene.id === 'apaga'}
          />
        </>
      );

    case 'neural':
      return (
        <>
          <div style={{...fullBlack}} />
          <NeuralGrid color={scene.colorAccent} nodeCount={45} />
        </>
      );

    case 'bios':
      return <BIOSBoot />;

    case 'strobe':
      return (
        <>
          <div
            style={{
              ...fullBlack,
              background: `linear-gradient(180deg, #0A0A0A 0%, ${scene.colorAccent}20 50%, #0A0A0A 100%)`,
            }}
          />
          <StrobeFlash color={scene.colorAccent} intensity={0.9} />
        </>
      );

    case 'void':
      return <VoidFade fadeIn={scene.id === 'end'} />;

    case 'fold': {
      const rotateX = Math.sin(frame * 0.05) * 20;
      const rotateY = Math.cos(frame * 0.03) * 15;
      const rotateZ = Math.sin(frame * 0.02) * 5;
      return (
        <div style={{...fullBlack}}>
          {/* Multiple nested cubes for bizarre depth */}
          {[1, 0.6, 0.3].map((scale, idx) => (
            <div
              key={idx}
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                width: 600 * scale,
                height: 600 * scale,
                transform: `translate(-50%, -50%) perspective(800px) rotateX(${rotateX + idx * 30}deg) rotateY(${rotateY + idx * 20}deg) rotateZ(${rotateZ}deg)`,
                border: `${2 - idx * 0.5}px solid ${scene.colorAccent}`,
                boxShadow: `0 0 ${30 + idx * 20}px ${scene.colorAccent}40, inset 0 0 ${30 + idx * 10}px ${scene.colorAccent}20`,
                zIndex: 2 + idx,
                opacity: 1 - idx * 0.2,
              }}
            >
              {Array.from({length: 6}, (_, i) => (
                <React.Fragment key={i}>
                  <div
                    style={{
                      position: 'absolute',
                      top: `${(i + 1) * 14.28}%`,
                      left: 0,
                      width: '100%',
                      height: 1,
                      backgroundColor: `${scene.colorAccent}40`,
                    }}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      left: `${(i + 1) * 14.28}%`,
                      top: 0,
                      height: '100%',
                      width: 1,
                      backgroundColor: `${scene.colorAccent}40`,
                    }}
                  />
                </React.Fragment>
              ))}
            </div>
          ))}
        </div>
      );
    }

    case 'glitch':
    default: {
      const noiseBlocks = Array.from({length: 14}, (_, i) => ({
        top: random(`gb-y-${i}-${frame % 4}`) * 100,
        height: 2 + random(`gb-h-${i}`) * 20,
        offset: (random(`gb-x-${i}-${frame % 3}`) - 0.5) * 60,
        color: i % 3 === 0 ? scene.colorAccent : i % 3 === 1 ? '#FF0000' : '#00FFFF',
        opacity: 0.06 + random(`gb-o-${i}`) * 0.1,
      }));

      return (
        <div style={{...fullBlack}}>
          {noiseBlocks.map((block, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                top: `${block.top}%`,
                left: 0,
                width: '100%',
                height: block.height,
                backgroundColor: block.color,
                opacity: block.opacity,
                transform: `translateX(${block.offset}px)`,
                mixBlendMode: 'screen',
              }}
            />
          ))}
        </div>
      );
    }
  }
};

/** Beat-reactive beat bar with glow */
const BeatBar: React.FC = () => {
  const {beatPhase, beatPulse} = useBeat();

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: `${beatPhase * 100}%`,
        height: 3 + beatPulse * 2,
        backgroundColor: '#2B3BE5',
        zIndex: 25,
        boxShadow: `0 0 ${10 + beatPulse * 20}px #2B3BE5, 0 0 ${beatPulse * 40}px #2B3BE580`,
      }}
    />
  );
};

/** BPM display with beat flash */
const BPMCounter: React.FC = () => {
  const {beatIndex, beatPulse} = useBeat();

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 20,
        right: 30,
        fontFamily: "'Courier New', monospace",
        fontSize: 14,
        color: `rgba(43, 59, 229, ${0.4 + beatPulse * 0.4})`,
        zIndex: 25,
        textShadow: beatPulse > 0.5 ? '0 0 10px #2B3BE560' : 'none',
      }}
    >
      110 BPM • {beatIndex}
    </div>
  );
};

/** MOSKV watermark */
const Watermark: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: 'absolute',
        top: 24,
        left: 30,
        fontFamily: "'Impact', 'Arial Black', sans-serif",
        fontSize: 16,
        fontWeight: 900,
        color: '#FFFFFF12',
        letterSpacing: '0.3em',
        zIndex: 25,
        textTransform: 'uppercase',
      }}
    >
      MOSKV
    </div>
  );
};

/** Timestamp overlay */
const Timestamp: React.FC = () => {
  const frame = useCurrentFrame();
  const seconds = Math.floor(frame / 30);
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(seconds % 60).padStart(2, '0');
  const ff = String(frame % 30).padStart(2, '0');

  return (
    <div
      style={{
        position: 'absolute',
        top: 24,
        right: 30,
        fontFamily: "'Courier New', monospace",
        fontSize: 13,
        color: '#FFFFFF15',
        zIndex: 25,
      }}
    >
      {mm}:{ss}:{ff}
    </div>
  );
};

/** Bizarre inverted flash — random full-frame color inversions */
const BizarreFlash: React.FC = () => {
  const frame = useCurrentFrame();
  const {isOnBar, barIndex} = useBeat();

  // Every ~12 bars, do a bizarre inversion
  const shouldInvert = barIndex > 0 && barIndex % 12 === 0 && (frame % Math.round(BAR_FRAMES * 12)) < 4;
  // Random color warp
  const isWarp = random(`bizarre-${frame}`) > 0.97;

  if (!shouldInvert && !isWarp) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 40,
        pointerEvents: 'none',
        mixBlendMode: shouldInvert ? 'difference' : 'exclusion',
        backgroundColor: shouldInvert ? '#FFFFFF' : `hsl(${random(`warp-h-${frame}`) * 360}, 100%, 50%)`,
        opacity: shouldInvert ? 0.85 : 0.15,
      }}
    />
  );
};

export const LlevaSalClip: React.FC = () => {
  return (
    <BeatReactor>
      <AbsoluteFill style={{backgroundColor: '#0A0A0A'}}>
        {/* Audio track */}
        <Audio src={staticFile('audio.wav')} />

        {/* Global camera shake */}
        <CameraShake intensity={0.8}>
          {/* Persistent atmospheric particles */}
          <ParticleField color="#2B3BE5" count={50} />

          {/* Scenes */}
          {SCENES.map((scene) => (
            <Sequence
              key={scene.id}
              from={scene.startFrame}
              durationInFrames={scene.durationFrames}
              name={scene.id}
            >
              <SceneTransition direction="in" duration={18}>
                <AbsoluteFill>
                  {/* Scene-specific particles (color-matched) */}
                  <ParticleField color={scene.colorAccent} count={25} />
                  <SceneBackground scene={scene} />
                  {scene.text && (
                    <GlitchText
                      text={scene.text}
                      boldPhrase={scene.boldPhrase}
                      colorAccent={scene.colorAccent}
                      fontSize={scene.id.startsWith('intro') ? 80 : scene.id === 'title' ? 96 : 52}
                    />
                  )}
                </AbsoluteFill>
              </SceneTransition>
            </Sequence>
          ))}

          {/* Naroa artwork flash-reveals (every 6 bars for more frequency = more bizarre) */}
          <ArtworkFlash frequency={6} flashDuration={10} />

          {/* Bizarre inversions and color warps */}
          <BizarreFlash />
        </CameraShake>

        {/* Persistent HUD (outside camera shake) */}
        <BeatBar />
        <BPMCounter />
        <Watermark />
        <Timestamp />
      </AbsoluteFill>
    </BeatReactor>
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
