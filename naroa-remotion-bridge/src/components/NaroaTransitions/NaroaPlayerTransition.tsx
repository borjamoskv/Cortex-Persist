import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  Img,
} from 'remotion';

export const NaroaPlayerTransition: React.FC<{
  currentImageUrl: string;
  nextImageUrl: string;
  title: string;
  direction: 'forward' | 'backward';
}> = ({ currentImageUrl, nextImageUrl, title, direction }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Phase 1: Exit current (Frame 0 to 15)
  // Phase 2: Enter next (Frame 10 to 30)
  
  const exitOpacity = interpolate(
    frame,
    [0, 15],
    [1, 0],
    { extrapolateRight: 'clamp' }
  );

  const exitScale = interpolate(
    frame,
    [0, 20],
    [1, 1.05],
    { extrapolateRight: 'clamp' }
  );

  const enterOpacity = interpolate(
    frame,
    [10, durationInFrames - 5],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const enterScale = interpolate(
    frame,
    [10, durationInFrames],
    [1.1, 1], // Inercia pesada
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  // Typography cinematic reveal
  const titleY = interpolate(
    frame,
    [15, durationInFrames - 10],
    [50, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const titleOpacity = interpolate(
    frame,
    [15, durationInFrames - 20],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', overflow: 'hidden' }}>
      {/* Saliente */}
      <AbsoluteFill style={{ opacity: exitOpacity, transform: `scale(${exitScale})` }}>
        <Img 
          src={currentImageUrl} 
          style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'grayscale(30%)' }} 
        />
      </AbsoluteFill>

      {/* Entrante */}
      <AbsoluteFill style={{ opacity: enterOpacity, transform: `scale(${enterScale})` }}>
        <Img 
          src={nextImageUrl} 
          style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
        />
      </AbsoluteFill>

      {/* Título de Obra Revelado */}
      <AbsoluteFill 
        style={{ 
          justifyContent: 'center', 
          alignItems: 'center',
          pointerEvents: 'none'
        }}
      >
        <h1 
          style={{
             fontFamily: 'Outfit, sans-serif',
             fontWeight: 300,
             fontSize: '7vw',
             color: '#EAEAEA',
             letterSpacing: '-0.02em',
             transform: `translateY(${titleY}px)`,
             opacity: titleOpacity,
             textTransform: 'uppercase'
          }}
        >
          {title}
        </h1>
      </AbsoluteFill>

      {/* Noise Overlay Cinematográfico Fijo */}
      <AbsoluteFill 
        style={{
          opacity: 0.04,
          mixBlendMode: 'overlay',
          background: 'url("https://upload.wikimedia.org/wikipedia/commons/7/76/1k_Dissolve_Noise_Texture.png") repeat',
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
