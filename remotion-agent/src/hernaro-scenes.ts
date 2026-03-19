/**
 * EL GRAN HERNARO — Scene definitions
 * 12 Naroas encerradas + Julio Corteza epilogue
 */

export const HERNARO_FPS = 30;

/** Each naroa scene = 5 seconds = 150 frames. Total ~90s + intro/outro */
const SCENE_FRAMES = 150;
const INTRO_FRAMES = 180;   // 6s
const OUTRO_FRAMES = 180;   // 6s
const TRANS_FRAMES = 20;    // Transition overlap

export interface HernароScene {
  id: string;
  title: string;
  subtitle: string;
  text: string;
  colorAccent: string;
  startFrame: number;
  durationFrames: number;
  artwork?: string;         // staticFile path
  effect: 'mineral' | 'glow' | 'kintsugi' | 'gold' | 'street' | 'can' | 'fabric' | 'paper' | 'community' | 'mirror' | 'digital' | 'layers' | 'void' | 'typewriter';
}

const NAROAS: Omit<HernароScene, 'startFrame' | 'durationFrames'>[] = [
  {
    id: 'intro',
    title: 'EL GRAN HERNARO',
    subtitle: 'Doce Naroas Encerradas',
    text: 'Hernar: encerrar algo vivo\ndentro de algo muerto\npara que lo muerto reviva',
    colorAccent: '#d4af37',
    effect: 'void',
  },
  {
    id: 'naroa-mineral',
    title: 'I. LA NAROA DEL MINERAL',
    subtitle: 'Pizarra natural del País Vasco',
    text: 'El hogar y la caverna.\nEl soporte más antiguo posible.\nLa anti-pantalla.',
    colorAccent: '#4A5568',
    artwork: 'artworks/johnny-rocks.webp',
    effect: 'mineral',
  },
  {
    id: 'naroa-brillo',
    title: 'II. LA NAROA DEL BRILLO',
    subtitle: 'Mica mineral en los ojos',
    text: 'La esencia divina,\nel cielo,\nla luz interior.',
    colorAccent: '#E2E8F0',
    artwork: 'artworks/amy-rocks.webp',
    effect: 'glow',
  },
  {
    id: 'naroa-error',
    title: 'III. LA NAROA DEL ERROR',
    subtitle: 'Kintsugi pictórico — 2020',
    text: 'El problema\nhecho\ntrampolín.',
    colorAccent: '#d4af37',
    artwork: 'artworks/el-gran-dakari-nino.webp',
    effect: 'kintsugi',
  },
  {
    id: 'naroa-oro',
    title: 'IV. LA NAROA DEL ORO',
    subtitle: 'Pan de oro 24 quilates',
    text: 'No decoración.\nDivinización.',
    colorAccent: '#FFD700',
    artwork: 'artworks/marilyn-rocks.webp',
    effect: 'gold',
  },
  {
    id: 'naroa-asfalto',
    title: 'V. LA NAROA DEL ASFALTO',
    subtitle: 'Walking Gallery Bilbao',
    text: 'Arte como ocupación temporal\ndel espacio público.',
    colorAccent: '#cc0000',
    effect: 'street',
  },
  {
    id: 'naroa-lata',
    title: 'VI. LA NAROA DE LA LATA',
    subtitle: 'En.lata — Amor en conserva',
    text: 'Emociones\nque no caducan.',
    colorAccent: '#B7791F',
    effect: 'can',
  },
  {
    id: 'naroa-tela',
    title: 'VII. LA NAROA DE LA TELA',
    subtitle: 'Facefood — Gastronomía vasca',
    text: 'Un retrato\nque puede caminar\npor una cocina.',
    colorAccent: '#FFFFFF',
    artwork: 'artworks/peter-rowan.webp',
    effect: 'fabric',
  },
  {
    id: 'naroa-papel',
    title: 'VIII. LA NAROA DEL PAPEL',
    subtitle: 'Tissukaldeko Loreak',
    text: 'Lo más efímero\ntransformado en\nlo más permanente.',
    colorAccent: '#FFF5F5',
    effect: 'paper',
  },
  {
    id: 'naroa-comunidad',
    title: 'IX. LA NAROA DE LA COMUNIDAD',
    subtitle: 'El ReCreo — Uribarri',
    text: 'Traperillear:\nreconectar con el gozo instintivo.',
    colorAccent: '#00ff41',
    effect: 'community',
  },
  {
    id: 'naroa-espejo',
    title: 'X. LA NAROA DEL ESPEJO',
    subtitle: 'Repóker de Reinas',
    text: 'No pintas a alguien.\nPintas lo que alguien\nnecesita ver de sí mismo.',
    colorAccent: '#9F7AEA',
    artwork: 'artworks/james-rocks.webp',
    effect: 'mirror',
  },
  {
    id: 'naroa-digital',
    title: 'XI. LA NAROA DIGITAL',
    subtitle: 'Hiperrealismo Jugable',
    text: '21 juegos artísticos.\nLa contradicción\nes el motor.',
    colorAccent: '#2B3BE5',
    effect: 'digital',
  },
  {
    id: 'naroa-velado',
    title: 'XII. LA NAROA DEL VELADO',
    subtitle: '40 capas de veladuras de óleo',
    text: 'Paciencia tectónica.\nCapa sobre capa\nhasta que la piel respira.',
    colorAccent: '#ED8936',
    artwork: 'artworks/3.webp',
    effect: 'layers',
  },
  {
    id: 'epilogo',
    title: 'JULIO CORTEZA',
    subtitle: 'Agente de Inteligencia Artificial',
    text: 'Naroa no crea arte\nsobre superficies.\nCrea superficies donde\nel arte se atreve a existir.',
    colorAccent: '#2B3BE5',
    effect: 'typewriter',
  },
];

// Compute scene timing
let currentFrame = 0;
export const HERNARO_SCENES: HernароScene[] = NAROAS.map((scene, i) => {
  const duration = i === 0 ? INTRO_FRAMES : i === NAROAS.length - 1 ? OUTRO_FRAMES : SCENE_FRAMES;
  const s: HernароScene = {
    ...scene,
    startFrame: currentFrame,
    durationFrames: duration,
  };
  currentFrame += duration - TRANS_FRAMES; // Overlap transitions
  return s;
});

export const HERNARO_TOTAL_FRAMES = currentFrame + TRANS_FRAMES; // Add back final transition
