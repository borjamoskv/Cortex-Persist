/**
 * Lyrics data for "Lleva sal en la sonrisa" — 110 BPM
 * Audio duration: ~239.6s → 7188 frames @ 30fps
 * 1 beat = 60/110 = 0.5454s ≈ 16.36 frames
 * 1 bar (4 beats) ≈ 65.45 frames ≈ 2.18s
 */

export const BPM = 110;
export const FPS = 30;
export const BEAT_FRAMES = (60 / BPM) * FPS; // ~16.36
export const BAR_FRAMES = BEAT_FRAMES * 4;    // ~65.45
export const TOTAL_DURATION_FRAMES = 7188;

export interface LyricScene {
  id: string;
  text: string;
  boldPhrase: string;
  startFrame: number;
  durationFrames: number;
  colorAccent: string;
  effect: 'glitch' | 'rain' | 'crt' | 'neural' | 'bios' | 'strobe' | 'void' | 'fold';
}

const bar = (n: number) => Math.round(BAR_FRAMES * n);
const atBar = (n: number) => Math.round(BAR_FRAMES * n);

export const SCENES: LyricScene[] = [
  {
    id: 'title',
    text: 'LLEVA SAL EN LA SONRISA',
    boldPhrase: 'SAL',
    startFrame: 0,
    durationFrames: bar(2), // ~4.4s
    colorAccent: '#2B3BE5',
    effect: 'glitch',
  },
  {
    id: 'algoritmo',
    text: 'El algoritmo busca la simetría en el caos. Cada línea de código es una oración que se repite.',
    boldPhrase: 'Ojo por ojo rojo',
    startFrame: atBar(2),
    durationFrames: bar(4), // ~8.7s
    colorAccent: '#00FF41',
    effect: 'rain',
  },
  {
    id: 'fragmenta',
    text: 'La realidad se fragmenta. Los píxeles se desprenden de la pantalla como escamas de un pez plateado.',
    boldPhrase: 'todo lo modo solo',
    startFrame: atBar(6),
    durationFrames: bar(4),
    colorAccent: '#C0C0C0',
    effect: 'glitch',
  },
  {
    id: 'liturgia-bit',
    text: 'La liturgia del bit continúa. El operador procesa la señal mientras el mundo exterior se desvanece.',
    boldPhrase: 'lodo de modo rojo',
    startFrame: atBar(10),
    durationFrames: bar(4),
    colorAccent: '#FF1A1A',
    effect: 'crt',
  },
  {
    id: 'melon',
    text: 'MELón CON JAMón',
    boldPhrase: 'MELón CON JAMón',
    startFrame: atBar(14),
    durationFrames: bar(3), // ~6.5s — 5/4 time shift
    colorAccent: '#FFD700',
    effect: 'strobe',
  },
  {
    id: 'corrompen',
    text: 'Los archivos se corrompen con elegancia. El mastering de la existencia requiere una compresión que destruye la esencia.',
    boldPhrase: 'oro de coro solo',
    startFrame: atBar(17),
    durationFrames: bar(6), // ~13s — build up x8
    colorAccent: '#FFD700',
    effect: 'glitch',
  },
  {
    id: 'arquitectura',
    text: 'La arquitectura se pliega sobre sí misma. Las dimensiones se cruzan en un nudo de cables.',
    boldPhrase: 'lomo de toro cojo',
    startFrame: atBar(23),
    durationFrames: bar(4),
    colorAccent: '#8B4513',
    effect: 'fold',
  },
  {
    id: 'pulso',
    text: 'El pulso del reloj marca el ritmo de la procesión. Los datos caminan descalzos sobre cristales de cuarzo.',
    boldPhrase: 'todo lo modo solo',
    startFrame: atBar(27),
    durationFrames: bar(4),
    colorAccent: '#00FFFF',
    effect: 'neural',
  },
  {
    id: 'red-neuronal',
    text: 'La red neuronal sueña con paisajes de geometría imposible. Las neuronas de silicio disparan impulsos.',
    boldPhrase: 'coro de lobo loco',
    startFrame: atBar(31),
    durationFrames: bar(4),
    colorAccent: '#9B59B6',
    effect: 'neural',
  },
  {
    id: 'pipeline',
    text: 'El pipeline de la conciencia se atasca. Las ideas se amontonan como restos de un naufragio.',
    boldPhrase: 'solo lo noto poco',
    startFrame: atBar(35),
    durationFrames: bar(4),
    colorAccent: '#3498DB',
    effect: 'rain',
  },
  {
    id: 'ultima',
    text: 'La última instrucción se ejecuta en el vacío. El puntero apunta a una dirección que ya no existe.',
    boldPhrase: 'todo lo modo solo',
    startFrame: atBar(39),
    durationFrames: bar(4),
    colorAccent: '#1A1A2E',
    effect: 'void',
  },
  {
    id: 'apaga',
    text: 'El sistema se apaga. La oscuridad es total, un negro absoluto que devora los restos de la interfaz.',
    boldPhrase: 'solo lo noto poco',
    startFrame: atBar(43),
    durationFrames: bar(3),
    colorAccent: '#0A0A0A',
    effect: 'crt',
  },
  {
    id: 'resurreccion',
    text: 'La resurrección es un reinicio frío. El BIOS carga las rutinas de inicio.',
    boldPhrase: 'todo lo modo solo',
    startFrame: atBar(46),
    durationFrames: bar(4),
    colorAccent: '#00FF41',
    effect: 'bios',
  },
  {
    id: 'liturgia-fin',
    text: 'La liturgia termina. El operador se levanta de la silla y camina hacia la salida.',
    boldPhrase: 'poco de modo rojo',
    startFrame: atBar(50),
    durationFrames: bar(4),
    colorAccent: '#FF1A1A',
    effect: 'crt',
  },
  {
    id: 'intercambio',
    text: 'El intercambio se ha completado. El precio ha sido pagado en ciclos de CPU y sudor de metal.',
    boldPhrase: 'todo lo modo solo',
    startFrame: atBar(54),
    durationFrames: bar(3),
    colorAccent: '#C0C0C0',
    effect: 'void',
  },
  {
    id: 'puerta',
    text: 'La puerta se cierra. El eco del último comando resuena.',
    boldPhrase: 'POCO COCÓN COMPRO',
    startFrame: atBar(57),
    durationFrames: bar(2),
    colorAccent: '#FFD700',
    effect: 'strobe',
  },
  {
    id: 'intro-1',
    text: 'Como poco cocón\nComiéndose el melón\nCon jam jam jam\n(mami, dámelo)',
    boldPhrase: 'poco cocón',
    startFrame: atBar(59),
    durationFrames: bar(4),
    colorAccent: '#FF6B35',
    effect: 'strobe',
  },
  {
    id: 'intro-2',
    text: 'Como poco cocón\nComiéndose el melón\nCon jam jam jam\n(mami, dámelo)',
    boldPhrase: 'poco cocón',
    startFrame: atBar(63),
    durationFrames: bar(4),
    colorAccent: '#FF6B35',
    effect: 'glitch',
  },
  {
    id: 'intro-3',
    text: 'Como poco cocón\nComiéndo',
    boldPhrase: 'poco cocón',
    startFrame: atBar(67),
    durationFrames: bar(4),
    colorAccent: '#FF6B35',
    effect: 'crt',
  },
  {
    id: 'end',
    text: '',
    boldPhrase: '',
    startFrame: atBar(71),
    durationFrames: TOTAL_DURATION_FRAMES - atBar(71),
    colorAccent: '#0A0A0A',
    effect: 'void',
  },
];
