# Naroa Remotion Bridge

Sovereign package for O(1) Web Transitions using `@remotion/player`.

## Usage in Next.js / Astro (React)

Install this local package in your main web project:
```bash
npm install ../naroa-remotion-bridge
```

Then mount the Player in your routing wrapper:

```tsx
import { Player } from '@remotion/player';
import { NaroaPlayerTransition } from 'naroa-remotion-bridge';

export const TransitionOverlay = () => {
  return (
    <Player
      component={NaroaPlayerTransition}
      inputProps={{
        currentImageUrl: '/images/obra_1_hq.webp',
        nextImageUrl: '/images/obra_2_hq.webp',
        title: 'LA PIEL Y LA SOMBRA',
        direction: 'forward'
      }}
      durationInFrames={60}
      fps={60}
      compositionWidth={1920}
      compositionHeight={1080}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 9999,
        pointerEvents: 'none' // Crucial para no bloquear el DOM
      }}
      autoPlay
      loop={false}
    />
  );
};
```
