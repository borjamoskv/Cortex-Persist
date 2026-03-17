import { useEffect } from 'react';

// Generative aesthetic palettes
const PALETTES = [
  // 1. Original Cyber Lime (Industrial Noir Base)
  { lime: '#CCFF00', abyssal: '#050505', violet: '#6600FF' },
  // 2. Radioactive Yellow
  { lime: '#E6FF00', abyssal: '#030303', violet: '#7A00FF' },
  // 3. Neon Mint
  { lime: '#00FF99', abyssal: '#010502', violet: '#0066FF' },
  // 4. Ghost White (Stark contrast)
  { lime: '#F0F0F0', abyssal: '#000000', violet: '#333333' },
  // 5. Blood Orange (Aggressive)
  { lime: '#FF3300', abyssal: '#050101', violet: '#FF0066' },
  // 6. Deep Magenta (Synthwave)
  { lime: '#FF00FF', abyssal: '#020005', violet: '#00FFFF' },
];

export function ThemeMutator({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // 1. Pick a random palette
    // We can mismatch background and accents for maximum glitch/mutation effect
    // But let's stick to cohesive palettes for sovereign aesthetic.
    const selected = PALETTES[Math.floor(Math.random() * PALETTES.length)];



    const root = document.documentElement;
    root.style.setProperty('--color-cyber-lime', selected.lime);
    root.style.setProperty('--color-abyssal-900', selected.abyssal);
    root.style.setProperty('--color-cyber-violet', selected.violet);

    // 2. Add a slight random rotation to background elements for structural mutation
    const skewDeg = (Math.random() - 0.5) * 2; // -1 to 1 degree
    root.style.setProperty('--global-skew', `${skewDeg}deg`);

    // Log the mutation for the diary
    console.log(`[CORTEX] UI Mutated. Seed: ${selected.lime}`);
  }, []);

  return <>{children}</>;
}
