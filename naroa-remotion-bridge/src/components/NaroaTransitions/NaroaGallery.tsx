import React from 'react';
import { Sequence, useVideoConfig } from 'remotion';
import { NaroaPlayerTransition } from './NaroaPlayerTransition';

export type NaroaAsset = {
  id: string;
  filename: string;
  type: string;
  size_kb: number;
  original_path: string;
};

export const NaroaAwwwardsGallery: React.FC<{
  assets: NaroaAsset[];
  transitionDuration?: number;
  itemDuration?: number;
}> = ({ assets, transitionDuration = 30, itemDuration = 120 }) => {

  if (!assets || assets.length === 0) {
    return <div style={{ color: 'white', fontFamily: 'Inter' }}>[ OMEGA CACHE ] Awaiting Data...</div>;
  }

  // Construcción termodinámica de línea temporal solapada
  return (
    <>
      {assets.map((asset, index) => {
        const nextAsset = assets[(index + 1) % assets.length];
        // Overlapping matemático: empieza cuando el anterior empieza a desvanecerse
        const startFrame = index * (itemDuration - transitionDuration);

        return (
          <Sequence
            key={asset.id}
            from={startFrame}
            durationInFrames={itemDuration}
          >
            <NaroaPlayerTransition
              currentImageUrl={`/naroa_assets/${asset.filename}`}
              nextImageUrl={`/naroa_assets/${nextAsset.filename}`}
              title={asset.filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ").toUpperCase()}
              direction="forward"
            />
          </Sequence>
        );
      })}
    </>
  );
};
