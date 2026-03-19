import {Composition} from 'remotion';
import {LlevaSalClip} from './LlevaSalClip';
import {ElGranHernaro} from './ElGranHernaro';
import {TOTAL_DURATION_FRAMES, FPS} from './lyrics';
import {HERNARO_TOTAL_FRAMES, HERNARO_FPS} from './hernaro-scenes';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="LlevaSalClip"
        component={LlevaSalClip}
        durationInFrames={TOTAL_DURATION_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="ElGranHernaro"
        component={ElGranHernaro}
        durationInFrames={HERNARO_TOTAL_FRAMES}
        fps={HERNARO_FPS}
        width={1920}
        height={1080}
      />
    </>
  );
};
